FROM almalinux:8

RUN mkdir -p /code && \
    yum update -y && \
    yum install python3-virtualenv python38 -y && \
    yum clean all
RUN curl https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh -o wait_for_it.sh && chmod +x wait_for_it.sh
COPY ./git_cacher/requirements.txt /tmp/requirements.txt
RUN cd /code && virtualenv -p python3.8 env && source env/bin/activate \
    && pip3 install -r /tmp/requirements.txt --no-cache-dir
COPY ./git_cacher/git_cacher.py /code/
WORKDIR /code
CMD ["/bin/bash", "-c", "source env/bin/activate && python git_cacher.py"]
