// SynchrO.cpp : Defines the entry point for the application.
//

#include "SynchrO.h"

#include <array>
#include <atomic>
#include <condition_variable>
#include <limits>
#include <memory>
#include <mutex>
#include <vector>

// Flow:
// - Server launches:
//	- recursive directory walk discovers files,
//	- each file mmap'd into an MMapRead structure,
//	- MMapReads forwarded to transmitter,
//
// Three channels are used:
//
//	1. s->c filenames
//	2. s<-c filename request
//	3. s->c filedata

struct Permissions
{
	uint64_t	m_permissions;
};

struct MMapRead
{
	std::string	m_filepath{ "" };		//! source-relative path
	void*		m_data{ nullptr };		//! pointer to the mapped data or 0
	size_t		m_size{ 0 };
	uint64_t	m_ctime, m_mtime;		//! created and modified time stamps
	Permissions	m_perms{};

	MMapRead(std::string filepath_);
	~MMapRead();

	void open(std::string filepath_);
	void reset(std::string filepath_)
	{
		close();
		if (!filepath_.empty())
			open(filepath_);
	}
	void close();

	void* const data() const noexcept { return m_data;  }
	size_t size() const noexcept { return m_size; }
};

namespace ThreadSafe
{
	namespace Mutexed
	{
		template<typename T, size_t Size>
		struct Histogram
		{
			std::array<T, Size>		m_log;
			size_t					m_readPos{ 0 };
			size_t					m_writePos{ 0 };
			std::mutex				m_mutex;
			std::condition_variable m_cv{ m_mutex };

			static constexpr size_t c_terminator = std::numeric_limits<decltype(m_readPos)>::max();

			void wrappingIncrement(size_t& pos)
			{
				if (++pos == Size)
					pos = 0;
			}

			template<typename... Args>
			void push(Args&&... args)
			{
				std::lock_guard lock(m_mutex);
				m_log[m_writePos] = T(std::forward<Args>(args...));
				wrappingIncrement(m_writePos);
				m_cv.notify_all();
			}

			void close()
			{
				std::lock_guard lock(m_mutex);
				m_readPos = c_terminator;
				m_cv.notify_all();
			}

			bool pop(T& into)
			{
				std::lock_guard lock(m_mutex);
				m_cv.wait(lock, []() { return m_readPos != m_writePos; });
				if (m_readPos == c_terminator)
					return false;
				into = std::move(m_log[m_readPos]);
				wrappingIncrement(m_readPos);
				return true;
			}
		};

		// Thread-safe queue of index values.
		template <size_t Size>
		struct MPSCIndexQueue
		{
			static constexpr size_t c_Terminator = std::numeric_limits<size_t>::max();

			std::string m_name;

			// The list of indexes we're hosting.
			std::array<size_t, Size> m_indices{};

			// To operate as a queue, we push/pop to the back,
			// so we need to know our depth.
			size_t				m_reservation{ 0 };
			std::atomic<size_t> m_depth{ 0 };
			bool				m_closing;

			// Not copy or movable
			MSPCIndexQueue(const MSPCIndexQueue&) = delete;
			MSPCIndexQueue(MSPCIndexQueue&&) = delete;

			MSPCIndexQueue(std::string name) : m_name(name) {}

			std::mutex				m_queueLock{};
			std::condition_variable m_queueCv{};

			void push(size_t index_)
			{
				std::lock_guard lock(m_queueLock);
				auto reservation = (m_reservation++) % Size;
				if (reservation - m_depth >= Size)
				{
					// Track how long we spend pending
					EventTrack scope(m_name.c_str());
					m_queueCv.wait(lock, [=]() { return reservation - m_depth >= Size; })
				}

				m_indices[reservation] = index_;
				m_queueCv.notify_all();
			}

			size_t pop()
			{
				std::lock_guard lock(m_queueLock);
				while (m_depth == m_reservation)
				{
					m_queueCv.wait(lock, [=]() { return m_depth == m_reservation; })
				}
				if (m_depth == c_Terminator)
					return m_depth;
				auto result = m_indices[m_depth++];
				if (m_depth == Size)
			}
		};
	}
}

struct Event
{
	const char* m_name;
	std::chrono::nanoseconds m_duration;

	Event(const char* name_, std::chrono::nanoseconds duration_);
};


ThreadSafe::Mutexed::Histogram<Event, 1 << 22> s_eventLog;

struct EventTrack
{
	using event_clock = std::chrono::steady_clock;

	event_clock::time_point	m_start{ event_clock::now() };
	const char* m_name;

	EventTrack(const char* name) : m_name(name) {}
	~EventTrack()
	{
		s_eventLog.push(m_name, std::chrono::nanoseconds(event_clock::now() - m_start));
	}
};

std::atomic<uint64_t> 
std::vector<std::unique_ptr<MMapRead>> g_mmaps;
std::vector<uint64_t> g_freeIndexes;
std::vector<uint64_t> g_loadingIndexes;
std::vector<uint64_t>


void source_service()
{
	Worker clientFiles;				// tell client which files are available
	Worker clientReqs;				// get client requests
	Worker transmitter;				// send the data to the client
	Worker mmapper{ transmitter };	// send mmaps to the transmitter

	DirectoryWalker walker(args.source);
	for (auto dir : walker)
	{
		client.forward(dir);
		mapper.forward(dir);
	}

	mapper.finish();
	transmitter.join();
}


int main(int argc, const char* argv[])
{
	parse_arguments();

	if (args.source)
		source_service();
	else
		destination_service();

	return 0;
}
