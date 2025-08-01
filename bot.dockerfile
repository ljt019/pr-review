FROM busybox:latest

# Install ripgrep static binary (essential for grep tool)
RUN wget https://github.com/BurntSushi/ripgrep/releases/download/14.1.0/ripgrep-14.1.0-x86_64-unknown-linux-musl.tar.gz && \
    tar xzf ripgrep-14.1.0-x86_64-unknown-linux-musl.tar.gz && \
    mv ripgrep-14.1.0-x86_64-unknown-linux-musl/rg /bin/rg && \
    chmod +x /bin/rg && \
    rm -rf ripgrep-14.1.0-x86_64-unknown-linux-musl*

# Create workspace directory
RUN mkdir -p /workspace

# Set working directory to workspace
WORKDIR /workspace

# Keep container running
CMD ["sleep", "3600"]