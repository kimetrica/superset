FROM python:3.5

RUN curl -sL https://deb.nodesource.com/setup_7.x | bash - && \
    apt-get install -y vim curl postgresql-client \
                       build-essential \
                       libssl-dev \
                       libffi-dev \
                       libsasl2-dev \
                       libldap2-dev \
                       git-core \
                       nodejs && \
    apt-get clean && \
    apt-get -y autoremove && \ 
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install the JavaScript client dependencies
ARG NPM_CONFIG_REGISTRY=https://registry.npmjs.org/
COPY superset/assets/package.json /usr/src/app/superset/assets/package.json
WORKDIR /usr/src/app/superset/assets
RUN git config --global url."https://".insteadOf git:// && \
    git config --global url."https://github.com".insteadOf git@github.com && \
    git config --global url."https://github.com".insteadOf ssh://git@github.com && \
    npm install -g yarn && \
    yarn

# Build the JavaScript client
WORKDIR /usr/src/app/superset/assets
COPY superset/assets /usr/src/app/superset/assets
RUN npm run sync-backend && npm run prod

WORKDIR /usr/src/app

# Install upstream Python dependencies
# Make sure editable installs aren't in the app src directory (because then they
# are no longer available if we mount the upstream source directly)
ARG PIP_TRUSTED_HOST=127.0.0.1
ARG PIP_INDEX_URL=https://pypi.python.org/simple/
COPY requirements/upstream.pip requirements/upstream.pip
RUN pip install --no-cache-dir --upgrade setuptools pip
RUN pip install --src /usr/src --no-cache-dir -r requirements/upstream.pip

# Install our Python dependencies
# Make sure editable installs aren't in the app src directory (because then they
# are no longer available if we mount the upstream source directly)
COPY requirements requirements
RUN pip install --src /usr/src --no-cache-dir -r requirements/kimetrica.pip

# Create the user and set up other mostly static layers that don't change
RUN useradd --create-home superset
ENV PYTHONIOENCODING UTF-8
ENV FLASK_APP=superset
EXPOSE 8000
ENTRYPOINT ["/usr/src/app/docker/superset/run_superset.sh"]

# Copy the main source code
COPY . /usr/src/app

# Install Superset as an editable package
# This will also check dependencies in case our requirements/upstream.pip file is out of date
RUN pip install --src /usr/src --no-cache-dir -e .

# This directory is a VOLUME in the override-setup, and if doesn't
# already exist when run_superset.sh runs with docker-compose.override.yml,
# it will be created with the wrong owner.
RUN mkdir -p docs/_build

# Set privs on writable directories
RUN chown -R superset:superset superset/static docs

# Switch to unprivileged user
USER superset
