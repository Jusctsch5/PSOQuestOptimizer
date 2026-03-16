# PSO Quest Optimizer Web Interface

This is a static web interface for the PSO Quest Optimizer, running entirely in the browser using Pyodide.
Pyodide allows python code to be run in the browser, without the need to install python or any dependencies on the client's machine.

## Setup for GitHub Pages

The web interface is automatically deployed to GitHub Pages via GitHub Actions. All Python modules and data files are copied into the deployment directory during the build process.

## Local Development

**Serve from repository root:**

```bash
cd PSOQuestOptimizer  # Go to repository root
python -m http.server 8000
```

Then open `http://localhost:8000/web/` in your browser.

**Note:** The interface uses `../` paths to access Python modules and data files from the repository root. This works when serving from the repo root. The deployment process copies all files into a single directory and sets the base path accordingly.

