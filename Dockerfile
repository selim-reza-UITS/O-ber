# # First we need a select ubuntu os and python version: 

# FROM python:3.12-slim
# # Base OS + Python preinstalled
# # slim = smaller image (less attack surface, faster pull)
# # You don’t need Ubuntu manually → Python image already has Debian inside

# #########################################################
# #########################################################
# #########################################################

# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1
# # PYTHONDONTWRITEBYTECODE → no .pyc files (cleaner containers)
# # PYTHONUNBUFFERED → logs show instantly (critical for Docker logs)



# #########################################################
# #########################################################
# #########################################################

# WORKDIR /app
# # Sets default directory
# # Every RUN, COPY, CMD happens inside /app
# # Automatically creates /app if it doesn’t exist


# #########################################################
# #########################################################
# #########################################################

# RUN apt-get update && apt-get install -y \
#     binutils \
#     libproj-dev \
#     gdal-bin \
#     libpq-dev \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# # Because Python packages often depend on OS libraries.
# # pip install sometimes needs Linux tools → install them before pip
# # rm -rf /var/lib/apt/lists/* → reduces image size (important)


# #########################################################
# #########################################################
# #########################################################

# COPY requirements.txt /app/
# RUN pip install --upgrade pip && pip install -r requirements.txt

# # Why not copy everything first? Because Docker caching.
# # If code changes → dependencies don’t reinstall
# # If requirements.txt changes → reinstall

# #########################################################
# #########################################################
# #########################################################


# COPY . /app/
# COPY ./scripts /app/scripts
# # Moving Django project is inside the container.


# #########################################################
# #########################################################
# #########################################################

# RUN chmod +x ./scripts/entrypoint.sh
# # Linux containers care about execution permissions. So given permission to entrypoint.sh


# #########################################################
# #########################################################
# #########################################################

# ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# # ENTRYPOINT:
# # Runs every time container starts

# # Used for:

# # waiting for DB

# # migrations

# # setup tasks

# # ENTRYPOINT = startup script
# # CMD = default command


# #########################################################
# #########################################################
# #########################################################


FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory inside the container
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq-dev \
    gcc \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Copy the scripts folder
COPY ./scripts /app/scripts

# Make entrypoint script executable
RUN chmod +x /app/scripts/entrypoint.sh

# Set the entrypoint
CMD ["/app/scripts/entrypoint.sh"]
