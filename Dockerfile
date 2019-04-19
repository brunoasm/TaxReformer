# Use anaconda as a parent image
FROM continuumio/miniconda3

# Get gnparser
RUN wget https://www.dropbox.com/s/lhlik0je9fmf164/gnparser-v0.8.0-linux.tar.gz && \
    tar xvf gnparser*gz && \
    cp gnparser /usr/local/bin && \
    rm -f gnparser*

# Set workdir and copy files
WORKDIR /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN conda config --add channels conda-forge && \
    conda install --yes --file requirements.txt && \ 
    conda clean --yes --all

# Run app.py when the container launches
ENTRYPOINT ["python", "TaxReformer.py"]
