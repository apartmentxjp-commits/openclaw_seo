#!/bin/bash

# Start Hugo server for the real estate site in the background
# -s: source directory, --bind: bind to all interfaces, -p: port, --appendPort=false: avoid port duplication in URLs
hugo server -s site --bind 0.0.0.0 -p 1313 --appendPort=false --baseURL http://localhost:1313 &

# Start the Next.js dev server in the foreground
npm run dev
