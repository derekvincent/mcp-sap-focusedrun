FROM python:3.13-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the MCP server package
RUN pip install --no-cache-dir .

# Create and switch to a non-root user for security
RUN useradd -m mcpuser
USER mcpuser

# Set the default port and expose it
ENV PORT=8000
ENV HOST=0.0.0.0
ENV TRANSPORT=sse
EXPOSE 8000

ENTRYPOINT ["mcp-sap-focusedrun"]