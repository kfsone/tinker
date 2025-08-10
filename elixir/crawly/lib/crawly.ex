defmodule ProcessAssetResources do

  def find_rules_files(dir) do
    File.ls!(dir)
    |> Enum.map(&Path.join(dir, &1))
    |> Enum.flat_map(fn path ->
      cond do
        # Recurse directories
        File.dir?(path) -> find_rules_files(path)
        # Otherwise we want files that end with '.resources'
        Path.extname(path) == ".rules" -> [path]
        true -> []
      end
    end)
  end

end

defmodule Crawly do
  @moduledoc """
  Documentation for `Crawly`.
  """

  @doc """
  Hello world.

  ## Examples

      iex> Crawly.hello()
      :world

  """
  def hello do
    :world
  end
end
