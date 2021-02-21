package main

import (
	"fmt"
	"github.com/NOX73/go-neural"
	"github.com/NOX73/go-neural/learn"
	"github.com/NOX73/go-neural/persist"
	"github.com/cheggaaa/pb"
	"math"
	"math/rand"
	"sort"
	"time"
)

// Board consists of 4 x 4 cells, but we're training on a single slice which can
// represent either a horizontal or vertical slice of the board:
const WIDTH = 4
// In the actual game, each tile can be empty or contain 2, 4, 8, 16, 32, 64, 128, 256, 512, or 1024
// These are powers of 2, which can be represented by their log2 / bitnumber, ie empty = 0,
// 2 = 1, 16 = 4, 1024 = 10.
const VALUES = 11
const PERMUTATIONS = 14641  // 11pow4

type Sample struct {
	BoardSlice []float64  // values in this slice
	Goal	   []float64  // 0 = has gap, 1 = has fold
}

var Samples []Sample

func makeSamples() {
	rand.Seed(time.Now().UTC().UnixNano())
	zeroes := 333
	Samples = make([]Sample, PERMUTATIONS + zeroes)

	zero := Sample{
		BoardSlice: []float64{0, 0, 0, 0},
		Goal: []float64{0, 0},
	}

	for i := 0; i < PERMUTATIONS; i++ {
		slice := &Samples[i]
		values := make([]int, WIDTH)
		slice.BoardSlice = make([]float64, WIDTH)
		seed := i
		for x := 0; x < WIDTH; x++ {
			value := seed % VALUES
			if value != 0 {
				values[x] = value
				slice.BoardSlice[x] = float64(value)
			}
			seed /= VALUES  // shift right
		}
		var hasGap, hasFold float64
		for x := 0; x < WIDTH - 1; x++ {
			if values[x] != 0 {
				if values[x+1] == 0 {
					hasGap = 1.0
				} else if values[x+1] == values[x] {
					hasFold = 1.0
				}
			}
		}
		for x := 0; hasFold < 0.1 && x < WIDTH -1 ; x++ {
			if values[x] == 0 {
				continue
			}
			for x2 := x + 1; x2  < WIDTH; x2++ {
				if values[x2] != 0 {
					if values[x2] == values[x] {
						hasFold = 1.0
					}
					break
				}
			}
		}
		slice.Goal = []float64{ hasGap, hasFold }
	}

	for i := 0; i < zeroes; i++ {
		Samples[PERMUTATIONS + i] = zero
	}

	fmt.Println("-- created", len(Samples), "samples")
}

func main() {
	makeSamples()

	// inputs consist of one neuron for each tile value
	const numInputs = WIDTH  // one neuron to represent each tile value

	net := neural.NewNetwork(WIDTH, []int{ 101, 41, 2 })
	net.RandomizeSynapses()

	testNetwork(net)

	trainingSpeed := 0.15

	for gen := 0; ; gen++ {
		fmt.Println("generation", gen)

		// train on the complete dataset a few times.
		track("training", 33 * len(Samples), func (_ int, progress chan<- bool) {
			for n := 0; n < 33; n++ {
				for i := 0; i < len(Samples); i++ {
					progress <- true
					learn.Learn(net, Samples[i].BoardSlice, Samples[i].Goal, trainingSpeed)
				}
			}
		})

		_, gapDelta, foldDelta, _ := testNetwork(net)

		if gapDelta >= 0.01 || foldDelta >= 0.01 {
			continue
		}

		fmt.Println("full evaluation")
		failedSamples := make([]Sample, 0, len(Samples))
		deltas := make([]float64, 0, len(Samples))
		for _, sample := range Samples {
			gapDelta, foldDelta := testSample(net, sample)
			if gapDelta > 0.01 || foldDelta > 0.01 {
				failedSamples = append(failedSamples, sample)
				delta := gapDelta
				if foldDelta > delta {
					delta = foldDelta
				}
				deltas = append(deltas, delta)
			}
		}
		if len(failedSamples) == 0 {
			fmt.Println("victory")

			fmt.Println("saving to trained-net.json")
			persist.ToFile("trained-net.json", net)
			return
		}

		sort.Slice(failedSamples, func (l,r int) bool {
			return deltas[l] > deltas[r]
		})

		fmt.Printf("** FAILED %d of %d samples\n", len(failedSamples), len(Samples))

		if len(failedSamples) < 10 {
			fmt.Println("-- SAVING")
			persist.ToFile("trained-net.json", net)
		}

		for idx, sample := range failedSamples[:5] {
			gapDelta, foldDelta := testSample(net, sample)
			fmt.Println(idx + 1, "gap", gapDelta, "fold", foldDelta, sample)
		}

		if len(failedSamples) < 2000 {
			fmt.Printf("retraining %d samples\n", len(failedSamples))
			totalCount := 0
			for totalCount < 1000 {
				for r := 1; r < len(failedSamples); r++ {
					for l := 0; l < r; l++ {
						learn.Learn(net, failedSamples[l].BoardSlice, failedSamples[l].Goal, 0.01)
						totalCount += 1
					}
				}
			}
		}
		if len(failedSamples) < 50 {
			trainingSpeed = 0.05
		} else if len(failedSamples) < 200 {
			trainingSpeed = 0.07
		} else if len(failedSamples) < 1000 {
			trainingSpeed = 0.09
		} else {
			trainingSpeed = 0.1
		}
	}
}

func testSample(net *neural.Network, sample Sample) (gapDelta, foldDelta float64) {
	outputs := net.Calculate(sample.BoardSlice)
	return math.Abs(outputs[0] - sample.Goal[0]), math.Abs(outputs[1] - sample.Goal[1])
}

func testNetwork(net *neural.Network) (evaluation, gapDelta, foldDelta, worst float64) {
	for _, sample := range Samples {
		sampleGapDelta, sampleFoldDelta := testSample(net, sample)
		if sampleGapDelta > worst {
			worst = sampleGapDelta
		}
		if sampleFoldDelta > worst {
			worst = sampleFoldDelta
		}
		gapDelta += sampleGapDelta
		foldDelta += sampleFoldDelta
		evaluation += learn.Evaluation(net, sample.BoardSlice, sample.Goal)
	}
	nSamples := float64(len(Samples))
	evaluation /= nSamples
	gapDelta /= nSamples
	foldDelta /= nSamples
	fmt.Println("eval", evaluation, "gap", gapDelta, "fold", foldDelta, "worst", worst)
	return
}

func track(what string, iterations int, action func(int, chan<- bool)) {
	fmt.Println("--", what)
	progressBar := pb.StartNew(iterations)
	defer progressBar.Finish()

	statusCh := make(chan bool, 128)
	go func () {
		defer close(statusCh)
		action(iterations, statusCh)
	}()

	progressBar.SetRefreshRate(500 * time.Millisecond)
	for range statusCh {
		progressBar.Increment()
	}
}

