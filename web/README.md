# PSO Quest Optimizer Web Interface

This is a static web interface for the PSO Quest Optimizer, running entirely in the browser using Pyodide.
Pyodide allows python code to be run in the browser, without the need to install python or any dependencies on the client's machine.

## Setup for GitHub Pages

1. Configure GitHub Pages to serve from the `web/` directory
2. The interface will automatically load Python modules and data files from the repository using `../` paths
3. GitHub Pages allows parent directory access, so this works without copying files

## Local Development

**Recommended: Serve from repository root**

```bash
cd PSOQuestOptimizer  # Go to repository root
python -m http.server 8000
```

Then open `http://localhost:8000/web/` in your browser.

**Note:** The code uses `../` paths to access files in the repo root. This works when:
- Serving from repo root (local dev) - page at `/web/` can use `../` to access repo root
- GitHub Pages serving from `web/` - GitHub Pages allows `../` paths

These are loaded via fetch and passed to Pyodide's filesystem.

