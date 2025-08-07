# Use an official Python image (works cross-platform)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy all project files
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose the Streamlit port
EXPOSE 8501

# Set environment variable to avoid sharing telemetry
ENV STREAMLIT_TELEMETRY_ENABLED=false

# Run the Streamlit app
CMD ["streamlit", "run", "Home.py"]
