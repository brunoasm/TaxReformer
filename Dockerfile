# Use anaconda as a parent image
FROM mambaorg/micromamba:focal

# tricks to reduce image size:https://jcristharif.com/conda-docker-tips.html

# Do not generate python bytecode
ENV PYTHONDONTWRITEBYTECODE=true

# Get GNparser
USER root
RUN apt-get update && apt-get install -y wget && \
    wget https://github.com/gnames/gnparser/releases/download/v1.6.7/gnparser-v1.6.7-linux.tar.gz && \
    tar xvf gnparser*gz && \
    cp gnparser /usr/local/bin && \
    rm -f gnparser* && \
    apt-get purge -y --auto-remove wget && \
    rm -rf /var/lib/apt/lists/*

# Install python packages and cleanup
RUN micromamba install --yes -n base -c conda-forge -c Anaconda \
          python \
          nomkl \
          fuzzywuzzy=0.18 \
          pandas=1.4.3 \
          python-Levenshtein=0.12.2 \
          requests && \
    micromamba clean --all --yes 

# Set workdir and copy files
WORKDIR /app
COPY TaxReformer.py /app

# Run when the container launches
WORKDIR /input
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "python", "/app/TaxReformer.py"]

