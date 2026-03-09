# Base Image
FROM node:20-slim

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    fonts-noto-cjk \
    hugo \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages google-generativeai requests matplotlib pillow pandas openai python-dotenv

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the source (for local dev, we will mount it, but we need node_modules)
COPY . .

# Default command
CMD ["npm", "run", "dev"]
