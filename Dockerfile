# Multi-stage build for faster builds and smaller final image
FROM mcr.microsoft.com/azure-functions/python:4-python3.10 AS builder

# Install system dependencies in builder stage
RUN apt-get update -y && \
    apt-get -y install gcc poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Copy certificate and configure
ADD ZscalerRootCertificate-2048-SHA256.crt /tmp/ZscalerRootCertificate-2048-SHA256.crt
RUN CERT_DIR=/usr/local/share/ca-certificates/ && \
    cp /tmp/ZscalerRootCertificate-2048-SHA256.crt $CERT_DIR && \
    update-ca-certificates && \
    openssl x509 -in /tmp/ZscalerRootCertificate-2048-SHA256.crt -out /tmp/ZscalarCert.pem -outform PEM

# Install Python dependencies with optimizations
COPY requirements.txt /
ENV PIP_CERT=/tmp/ZscalarCert.pem
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install dependencies with CPU-only PyTorch
RUN pip install --upgrade pip && \
    pip install -r /requirements.txt \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host download.pytorch.org \
    --no-cache-dir

# Final stage - smaller runtime image
FROM mcr.microsoft.com/azure-functions/python:4-python3.10

ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only runtime dependencies
RUN apt-get update -y && \
    apt-get -y install poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /home/site/wwwroot
