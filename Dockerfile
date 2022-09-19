# Use anaconda as a parent image
FROM continuumio/miniconda3

# Get gnparser
RUN wget https://github.com/gnames/gnparser/releases/download/v1.6.7/gnparser-v1.6.7-linux.tar.gz && \
    tar xvf gnparser*gz && \
    cp gnparser /usr/local/bin && \
    rm -f gnparser*

# Install python packages
RUN conda config --add channels conda-forge && \
    conda install --yes fuzzywuzzy=0.15.1 pandas=0.24.2 python-Levenshtein=0.12.0 && \ 
    conda clean --yes -i -l -t

# Set workdir and copy files
WORKDIR /app
ADD TaxReformer.py /app

# Run when the container launches
WORKDIR /input
ENTRYPOINT ["python", "/app/TaxReformer.py"]
