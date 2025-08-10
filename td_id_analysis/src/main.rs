extern crate bit_vec;
extern crate rusqlite;      // for sqlite access

use rusqlite::{Connection, Result as SqlResult};

use std::env;
use std::path::Path;


// Structure for capturing the distribution of ids for a given seed.
#[derive(Debug)]
struct Distrib {
    seed: u64,
    max_pop: usize,
    min_pop: usize,
    max_inst: usize,
    min_inst: usize,
    used: usize,
    unused: usize,
    avg_bucket_pop: f64,
    avg_potential: f64,
    distribution: f64,
}


fn fetch_station_ids(db_path: &Path) -> SqlResult<Vec<u64>> {
    let conn = Connection::open(db_path)?;
    let mut stmt = conn.prepare("SELECT station_id FROM Station ORDER BY station_id ASC")?;
    let ids = stmt
        .query_map([], |row| row.get(0))?
        .collect::<Result<Vec<u64>, rusqlite::Error>>()?;
    Ok(ids)
}


fn analyze_distribution(ids: &Vec<u64>, seed: u64) -> Distrib {
    let mut buckets = vec![0usize; seed as usize];

    for id in ids {
        let index = (id % seed) as usize;
        buckets[index] += 1;
    }

    let (used, unused): (Vec<usize>, Vec<usize>) = buckets.iter().partition(|&&count| count > 0);
    let used_count = used.len();
    let unused_count = unused.len();
    let max_pop = *used.iter().max().unwrap_or(&0);
    let min_pop = *used.iter().min().unwrap_or(&0);
    let max_inst = used.iter().filter(|&&x| x == max_pop).count();
    let min_inst = used.iter().filter(|&&x| x == min_pop).count();
    let total_ids = ids.len() as f64;
    let avg_bucket_pop = if used_count > 0 { total_ids / used_count as f64 } else { 0.0 };
    let avg_potential = total_ids / seed as f64;
    let distribution = if max_pop != 0 { min_pop as f64 / max_pop as f64 } else { 0.0 };

    Distrib {
        seed,
        max_pop,
        min_pop,
        max_inst,
        min_inst,
        used: used_count,
        unused: unused_count,
        avg_bucket_pop,
        avg_potential,
        distribution,
    }
}

fn main() -> Result<(), String> {
    // Get the database path.
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        return Err(format!("error: usage: {} <path to .db file>", args[0]));
    }

    // Retrieve the list of IDs.
    let db_path = match Path::new(&args[1]).canonicalize() {
        Err(e) => return Err(format!("error: invalid db path: {}: {}", e.to_string(), &args[1])),
        Ok(path) => path,
    };
    let ids = match fetch_station_ids(&db_path) {
        Err(e) => return Err(format!("error: {}: {}", args[1], e.to_string())),
        Ok(ids) => ids,
    };

    let count_ids = ids.len();
    if count_ids == 0 {
        return Err(format!("error: {}: no ids in station table", args[1]));
    }

    let min_ids   = *ids.first().unwrap();
    let max_ids   = *ids.last().unwrap();
    let range_ids      = max_ids - min_ids;

    println!("-- ids: {count_ids}, {min_ids}->{max_ids} a range of {range_ids}");

    let mut most_compact = 128;

    let low_seed = ids.len() as u64 / 8;  // Start with a seed that would require 8 ids per bucket
    let max_seed = (3 * ids.len()+1).next_power_of_two() as u64;

    println!("exploring {low_seed}-{max_seed}");

//    let first_thread = std::thread::spawn(|| {
    let mut winner: u64 = 0;
        for seed in low_seed..=(max_seed*4) {
            let mut space = bit_vec::BitVec::from_elem(seed as usize, false);
            let mut unique = true;
            for id in &ids {
                let bit = id % seed;
                if space.get(bit as usize).unwrap() {
                    // bit is already set, collision
                    unique = false;
                    break
                }
                space.set(bit as usize, true);
            }
            if !unique {
                if seed % 10000 == 0 {
                    print!("...{}\r", seed);
                    use std::io::Write;
                    std::io::stdout().flush().unwrap();
                }
                continue
            }
            println!("found unique spacing: {}", seed);
            winner = seed;
            break;
        }

    if winner != 0 {
        return Ok(());
    }
    // });
    // first_thread.join().unwrap();

    for seed in low_seed..=max_seed {
        let dist = analyze_distribution(&ids, seed);
        if dist.max_pop < most_compact {
            println!("{}: {}/bucket({}x) <-> {}/bucket({}x). pop: {}, empty: {}. avg(pop: {}, pot: {}). distrib: {}",
                dist.seed,
                dist.max_pop, dist.max_inst,
                dist.min_pop, dist.min_inst,
                dist.used, dist.unused,
                dist.avg_bucket_pop, dist.avg_potential,
                dist.distribution,
            );
            most_compact = dist.max_pop;
            if most_compact == 1 {
                break
            }
        }
    }

    println!("finished: most_compact == {}", most_compact);

    Ok(())
}
