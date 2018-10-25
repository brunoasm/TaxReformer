# TaxReformer

This is a python program that uses [Open Tree Taxonomy](https://tree.opentreeoflife.org/about/taxonomy-version/ott3.0) and [Global Names Architecture](http://globalnames.org) to update a list of species or genus names, possibly with spell errors.

It tries to use Open Tree Taxonomy whenever possible, pulling information from other databases in case a name is not found there. The source of information retrieved is saved in the output, so records not on OTT can be easily filtered out.

It looks up the provided names in these databases and returns a list of most likely matches, including nomenclatural updates (in case of a synonym) and taxonomic hierarchy.

## Dependencies

This script runs on python 2.7 and needs the following python packages:
```
argparse
requests
pygibif
pandas
fuzzywuzzy
requests
```

Additionally, you need to download [GNparser](https://github.com/GlobalNamesArchitecture/gnparser#command-line-tool-and-socket-server): https://github.com/GlobalNamesArchitecture/gnparser#command-line-tool-and-socket-server. TaxReformer is compatible with GNparser v. 1.0.2.


In case GNparser is not on your $PATH, you need to provide its location (see usage below).


## Input
Default input format is a csv table containing columns named **genus** and **species**

In Church, Seth et al, we used a text file representing a python dictionary as input. This format can be accepted by using the flag `-d` (see options below)

## Output
After a successful run, the program will write two output files names `matched_names.csv` and `unmatched_names.csv`, for names that could and could not be matched, respectively. These include all columns initially present in the input data table, as well as new columns with information retrieved by TaxReformer.


## Options

`-h` or `--help` Shows help

`-p` or `--gnparser` Path to GNparser executable. Not needed if it is on `$PATH`

`-o` or `--overwrite` Overwrite taxonomic information if available. Without this flag, the program skips records that already have it.


`-g` or `--genus-search` Use this if you want to ignore species names and search for genera only

`-c` or `--context` Taxonomic context to use for Open Tree Taxonomy (see [Open Tree of Life API](https://github.com/OpenTreeOfLife/germinator/wiki/TNRS-API-v3#contexts) for options). Defaults to **"All life"**

`-f` or `--tax-filter` Taxonomy contexts to use for other services. This is a comma-separated list of names of higher taxa in which queries must be included. Used to filter results from services other than Open Tree Taxonomy. A result matching any taxon in the list will be kept. Therefore, if a result is not included in any of these higher taxa, it will be excluded. 

`-d` or `--dict-input` Input and output as dictionaries instead of a table

## Examples

To see available options, simply type:
```python TaxReformer.py -h```

To find Arthropod names from a file named **input.csv**:

```python TaxReformer.py --context Arthropods --tax-filter Arthropoda input.csv```

To find bird names from a file named **input.csv**:

```python TaxReformer.py --context Birds --tax-filter Aves input.csv```

Same as before, but giving the path to GNparser (in the same folder as the input)

```python TaxReformer.py --gnparser ./gnparser --context Birds --tax-filter Aves input.csv```

The folder [examples](./examples/) contains a test input file and the expected output when running:

```python TaxReformer.py examples/input.csv```

## Warnings

This program was developed for a specific application and I am slowly working to make it more generally useful. If you want to use it and run into trouble, don't hesitate adding an issue: https://github.com/brunoasm/TaxReformer/issues

The program tries its best to find your names in some database, but different databases have different taxon coverages, levels of information and API require different inputs. For that reason, it is hard to make bulk searches: each name is searched individually, and this might happen several times if a match is not easily found. Open Tree of Life and Global Names Server might get mad at you if you try too many names, therefore making thousands or millions of requests to their servers. You should only use this tool for a small number of names each time you run. In our case, we searched a little less than 10,000 records, which took about one day.

Since each database uses different higher taxonomies, it is hard to delimit contexts. For example, Open Tree Taxonomy uses *Birds* to constrain search to birds, but to constrain on other databases we need to filter out taxa not contained in *Aves*. To delimit search to your taxa of interest, you will have to play both with `--context` and `tax-filter` (see examples above)

# Author

This program was written by [Bruno de Medeiros](https://github.com/brunoasm). For now, you can cite the following in case you use it:

`de Medeiros BAS. 2018. TaxReformer. Available at: https://github.com/brunoasm/TaxReformer`








