using System;
using System.Collections.Concurrent;

namespace SynchrO
{
	class Synchro
	{
		static void RunServer(string port, string path)
		{
			Console.WriteLine($"-- Server mode: port {port} serving {path}");
			using (var pathQueue = new BlockingCollection<string>())
			{

			}

		}
		static void RunClient(string host, string path)
		{
			Console.WriteLine($"-- Client mode: host {host} to {path}");
		}

		static bool RunMode(string[] args)
		{
			var mode = args[0].ToLower();
			var service = args[1];
			var path = args[2];
			Action<string, string> handler = null;

			if (mode == "server")
				handler = RunServer;
			else if (mode == "client")
				handler = RunClient;
			else
			{
				Console.Error.WriteLine($"** ERROR: Unrecognized mode: {mode}");
				return false;
			}
		
			try
			{
				handler(service, path);
				Environment.Exit(0);
			}
			catch (Exception e)
			{
				Console.Error.WriteLine($"** ERROR: {e.Message}");
				Environment.Exit(1);
			}
			return true;
		}

		static void Main(string[] args)
		{
			if (args.Length == 3)
			{
				if (RunMode(args))
					Environment.Exit(0);
			}

			Console.Error.WriteLine("Usage:");
			Console.Error.WriteLine("  synchro server <port> <path>");
			Console.Error.WriteLine("  synchro client <host:port> <path>");
			Environment.Exit(1);
		}
	}
}
