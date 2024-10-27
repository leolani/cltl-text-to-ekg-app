# syntax = docker/dockerfile:1.2

FROM python:3.9 as base

SHELL ["/bin/bash", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
        less \
        vim \
        gcc \
        build-essential \
        zlib1g-dev \
        wget \
        unzip \
        cmake \
        gfortran \
        libblas-dev \
        liblapack-dev \
        libatlas-base-dev \
       # libasound-dev \
       # libportaudio2 \
      #  libportaudiocpp0 \
       # portaudio19-dev \
       # ffmpeg \
        libsm6 \
        libxext6 \
        default-jre \
    && apt-get clean

# Get Rust; NOTE: using sh for better compatibility with other base images
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
RUN curl -fsSL https://ollama.com/install.sh | sh

# Add .cargo/bin to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

FROM base as build

SHELL ["/bin/bash", "-c"]

WORKDIR /leolani-text-to-ekg
COPY . ./


RUN make clean
RUN ollama serve & sleep 5 && make build
RUN make build

#RUN make clean & make build & make build

# To build a specfic stage only use the --target option, e.g.:
# docker build --target build --tag build:0.0.1 .
FROM base as leolani

COPY --from=build /leolani-text-to-ekg/app /leolani-text-to-ekg/app/
COPY --from=build /root/nltk_data /root/nltk_data

WORKDIR /leolani-text-to-ekg/app

RUN rm spacy.lock; make spacy.lock project_dependencies=""

# Copy the models from the base stage
COPY --from=build /root/.ollama/models /root/.ollama/models
# RUN rm ollama.lock; ollama serve & sleep 5 && make ollama.lock project_dependencies=""

WORKDIR /leolani-text-to-ekg/app/py-app

RUN printf '#!/bin/bash\nollama serve &\nsource /leolani-text-to-ekg/app/venv/bin/activate\npython app.py "$@"\n' > run.sh
RUN chmod +x run.sh

ARG NAME
CMD ./run.sh --name $NAME
