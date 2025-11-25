.PHONY: install install-backend install-frontend dev run backend frontend clean setup help

# Default target
help:
	@echo "LLM Council - Available commands:"
	@echo ""
	@echo "  make setup      - Create .env file (interactive)"
	@echo "  make install    - Install all dependencies"
	@echo "  make dev        - Run both backend and frontend"
	@echo "  make backend    - Run backend only (port 8001)"
	@echo "  make frontend   - Run frontend only (port 5173)"
	@echo "  make clean      - Remove generated files"
	@echo ""

# Setup .env file
setup:
	@if [ -f .env ]; then \
		echo ".env file already exists"; \
	else \
		read -p "Enter your OpenRouter API key: " key; \
		echo "OPENROUTER_API_KEY=$$key" > .env; \
		echo ".env file created"; \
	fi

# Install all dependencies
install: install-backend install-frontend
	@echo ""
	@echo "All dependencies installed!"
	@echo "Run 'make setup' to configure your API key, then 'make dev' to start."

install-backend:
	@echo "Installing Python dependencies..."
	uv sync

install-frontend:
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

# Run both services
dev run:
	@./start.sh

# Run backend only
backend:
	uv run python -m backend.main

# Run frontend only
frontend:
	cd frontend && npm run dev

# Clean generated files
clean:
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf .venv
	rm -rf __pycache__
	rm -rf backend/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned!"
