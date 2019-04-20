# TaxReformer

This python program uses [Open Tree Taxonomy](https://tree.opentreeoflife.org/about/taxonomy-version/ott3.0) and [Global Names Architecture](http://globalnames.org) to update a list of species or genus names, possibly containing spell errors.

It tries to use Open Tree Taxonomy whenever possible, pulling information from other databases in case a name is not found there. The source of information retrieved is saved in the output, so records not on OTT can be easily filtered out.

In addition to corrected names with nomenclatural updates (in case of a synonym), the full taxonomic hierarchy is also returned. This tool was first used to study the evolution of insect eggs, and we will soon submit the manuscript.

## Dependencies

This script runs on python 3 and needs the following python libraries:
```
pandas
fuzzywuzzy
```

Additionally, you need to download [GNparser](https://gitlab.com/gogna/gnparser). TaxReformer is compatible with GNparser v. 0.8.0.


In case GNparser is not installed in a folder in your `$PATH`, you need to provide its location (see usage below).

There is a docker image available for this program, which includes all dependencies. If you have [Docker](https://www.docker.com) installed, use the following to run the latest version:

```
docker run -v $PWD:/app brunoasm/taxreformer input.csv 
```
(Assuming the input file is named input.csv - see information on input below)

## Input
Default input format is a csv table containing a column named **name** including the names to be searched. Other columns are ignored and will be maintained in the output. See folder [examples](examples/) for a valid input file.

## Output
After a successful run, the program will write two output files names `matched_names.csv` and `unmatched_names.csv`, for names that could and could not be matched, respectively. These include all columns initially present in the input data table, as well as new columns with information retrieved by TaxReformer.


## Options

`-h` or `--help` Shows help

`-o` or `--output` Prefix to add to output files. Default is `output`.

`-p` or `--gnparser` Path to GNparser executable. Not needed if it is on `$PATH`

`-c` or `--context` Taxonomic context to use for Open Tree Taxonomy (see [Open Tree of Life API](https://github.com/OpenTreeOfLife/germinator/wiki/TNRS-API-v3#contexts) for options). Defaults to **"All life"**

`-f` or `--tax-filter` Taxonomy contexts to use for other services. This is a comma-separated list of names of higher taxa in which queries must be included. Used to filter results from services other than Open Tree Taxonomy. A result matching any taxon in the list will be kept. Therefore, if a result is not included in any of these higher taxa, it will be excluded. 

## Examples

1. To see available options, simply type: ```python TaxReformer.py -h```

   With docker, use: ```docker run -v $PWD:/app brunoasm/taxreformer -h```

2. To find Arthropod names from a file named **input.csv**:

```python TaxReformer.py --context Arthropods --tax-filter Arthropoda input.csv```

   With docker, use:
   
```docker run -v $PWD:/app brunoasm/taxreformer --context Arthropods --tax-filter Arthropoda input.csv```

3. To find bird names from a file named **input.csv**:

```python TaxReformer.py --context Birds --tax-filter Aves input.csv```

   With docker, use:
   
```docker run -v $PWD:/app brunoasm/taxreformer --context Birds --tax-filter Aves input.csv```

4. Same as before, but giving the path to GNparser (in the same folder as the input)

```python TaxReformer.py --gnparser ./gnparser --context Birds --tax-filter Aves input.csv```

5. To find names of termites, considering that they might be classified under roaches in some databases. Notice also that Open Tree of Life does not have a context for termites, so we will use insects instead:

```python TaxReformer.py --context Insects --tax-filter Isoptera,Blattodea,Termitoidea,Blattaria input.csv```

 With docker, use:
 
```docker run -v $PWD:/app brunoasm/taxreformer --context Insects --tax-filter Isoptera,Blattodea,Termitoidea,Blattaria input.csv```

The folder [examples](./examples/) contains a test input file and the expected output when running:

```python TaxReformer.py examples/input.csv```

## Warnings

This program was developed for a specific application and I am slowly working to make it more generally useful. If you want to use it and run into trouble, don't hesitate adding an issue: https://github.com/brunoasm/TaxReformer/issues

The program tries its best to find your names in some database, but different databases have different taxon coverages and APIs also require different inputs. For that reason, it is hard to make bulk searches: each name will be searched individually, and this might happen several times per name if a match is not easily found. Open Tree of Life and Global Names Server might get mad at you if you make thousands or millions of requests to their servers. You should only use this tool for a somewhat small number of names each time you run. In our case, we searched a little less than 10,000 records, which took about one day.

Since each database uses different higher taxonomies, it is hard to delimit contexts. For example, Open Tree Taxonomy uses *Birds* to constrain search to birds, but to constrain the same search on other databases we need to filter out taxa not contained in *Aves*. To delimit search to your taxa of interest, you will have to play both with `--context` and `tax-filter` (see examples above)

# Author

This program was written by [Bruno de Medeiros](https://github.com/brunoasm). For now, you can cite the following in case you use it:

`de Medeiros BAS. 2018. TaxReformer. Available at: https://github.com/brunoasm/TaxReformer`








