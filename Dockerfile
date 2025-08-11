# Define build argument for GPU support (default: false)
ARG USE_GPU=false

# Choose base image based on GPU flag
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 AS base-true
FROM ubuntu:22.04 AS base-false
FROM base-${USE_GPU}

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_PRIORITY=high
ENV HOME=/root

# Conditionally set CUDA environment variables
ARG USE_GPU
RUN if [ "$USE_GPU" = "true" ]; then \
    echo "Setting up CUDA and GPU support"; \
    echo 'export PATH=/usr/local/cuda/bin:${PATH}' >> /etc/profile.d/cuda.sh; \
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}' >> /etc/profile.d/cuda.sh; \
    echo 'export NVIDIA_VISIBLE_DEVICES=all' >> /etc/profile.d/cuda.sh; \
    echo 'export NVIDIA_DRIVER_CAPABILITIES=compute,utility' >> /etc/profile.d/cuda.sh; \
    chmod +x /etc/profile.d/cuda.sh; \
fi

# Set up proper locale for UTF-8 and emoji support will be configured after installing locales

# Add Docker's official GPG key and repository
RUN apt-get update && \
    apt-get -y install ca-certificates curl gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install system packages
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install \
    build-essential \
    gettext-base \
    locales \
    wget \
    # Docker packages
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin \
    # UI Requirements
    xvfb \
    xterm \
    kitty \
    xdotool \
    scrot \
    imagemagick \
    mutter \
    x11vnc \
    x11-xserver-utils \
    fonts-noto-color-emoji \
    # Python requirements
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    curl \
    git \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    # Network tools
    net-tools \
    netcat \
    lsof \
    # Development tools
    apt-utils \
    nano \
    tree \
    htop \
    jq \
    psmisc \
    ncdu \
    strace \
    vim \
    tig \
    ripgrep \
    fd-find \
    bat \
    bc \
    cargo \
    # Audio support
    pulseaudio \
    alsa-utils \
    libasound2-plugins \
    mpg123 \
    pulseaudio-utils \
    # PPA req
    software-properties-common && \
    # Setup Firefox repository
    add-apt-repository ppa:mozillateam/ppa && \
    # Install desktop applications
    apt-get install -y --no-install-recommends \
    libreoffice \
    firefox-esr \
    x11-apps \
    xpdf \
    gedit \
    xpaint \
    tint2 \
    galculator \
    pcmanfm \
    pciutils \
    unzip && \
    apt-get clean

# Install Node.js 20+ and npm 11+
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    npm install -g @google/gemini-cli

# Install Google Cloud SDK
RUN apt-get update && apt-get install -y apt-transport-https ca-certificates gnupg && \
    mkdir -p /usr/share/keyrings && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && apt-get install -y google-cloud-sdk

# Install OpenSSH server
RUN apt-get update && apt-get install -y openssh-server && \
    mkdir -p /var/run/sshd && \
    echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'root:password' | chpasswd

# Create symlink so the default 'firefox' command uses our launcher script
RUN ln -sf /usr/local/bin/launch_firefox /usr/bin/firefox

# Install and configure noVNC
RUN git clone --branch v1.5.0 https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone --branch v0.12.0 https://github.com/novnc/websockify /opt/noVNC/utils/websockify && \
    ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html && \
    chmod -R 755 /opt/noVNC

# Set up Python and ensure proper permissions
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    python3 -m pip install --upgrade pip==23.1.2 setuptools==58.0.4 wheel==0.40.0 && \
    python3 -m pip config set global.disable-pip-version-check true && \
    mkdir -p /tmp/outputs && \
    chmod 777 /tmp/outputs

# Install Python requirements
COPY requirements.txt /tmp/
RUN python3 -m pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install PyTorch with or without CUDA support based on build arg
ARG USE_GPU
RUN if [ "$USE_GPU" = "true" ]; then \
    echo "Installing PyTorch with CUDA 12.4 support..."; \
    python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124; \
else \
    echo "Installing PyTorch CPU-only version (saves ~13GB)..."; \
    python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
fi

# Install browser automation tools
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz && \
    tar -xzf geckodriver-v0.33.0-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-v0.33.0-linux64.tar.gz && \
    python3 -m pip install selenium==4.30.0 webdriver-manager==4.0.2

# Deploy system files
COPY deploy/image/ /

# Deploy Python package
COPY inXeption/ /opt/inXeption/lib/inXeption/

# Generate and configure locale for proper UTF-8 and emoji support
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Create required directories
RUN mkdir -p /host /var/www/html

# Set display configuration
ARG DISPLAY_NUM=1
ARG HEIGHT=768
ARG WIDTH=1024
ENV DISPLAY_NUM=$DISPLAY_NUM
ENV HEIGHT=$HEIGHT
ENV WIDTH=$WIDTH

# Setup Docker socket directory and permissions
RUN mkdir -p /var/run/docker && \
    chmod 2775 /var/run/docker

# Set up PulseAudio for containerized audio
RUN mkdir -p /etc/pulse
COPY deploy/image/etc/pulse/client.conf /etc/pulse/

# Create directory for sound files
RUN mkdir -p /opt/inXeption/media/sounds

WORKDIR /opt/inXeption
ENTRYPOINT ["bin/entrypoint.sh"]
