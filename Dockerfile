# Use anaconda as a parent image
FROM continuumio/miniconda3:23.5.2-0

# tricks to reduce image size:https://jcristharif.com/conda-docker-tips.html

# Do not generate python bytecode
ENV PYTHONDONTWRITEBYTECODE=true

# Get GNparser
RUN wget https://github.com/gnames/gnparser/releases/download/v1.6.7/gnparser-v1.6.7-linux.tar.gz && \
    tar xvf gnparser*gz && \
    cp gnparser /usr/local/bin && \
    rm -f gnparser*

# Install python packages and cleanup
RUN conda config --add channels conda-forge && \
    conda install --freeze-installed --yes nomkl fuzzywuzzy=0.18 pandas=1.4.3 python-Levenshtein=0.12.2 requests && \
    conda clean -afy && \
    find /opt/conda/ -follow -type f -name '*.pyc' -delete

# Set workdir and copy files
WORKDIR /app
ADD TaxReformer.py /app

# Run when the container launches
WORKDIR /input
ENTRYPOINT ["python", "/app/TaxReformer.py"]
