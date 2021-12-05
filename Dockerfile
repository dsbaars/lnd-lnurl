# Use official image, so it can be used on Intel PCs, Apple Silicon (M1) and Raspberry Pi's
FROM python:3.9-alpine3.14

WORKDIR /code
RUN apk --update --upgrade add --no-cache g++ gcc musl-dev zlib-dev \ 
    libffi-dev cairo-dev pango-dev gdk-pixbuf-dev \
    && rm -rf /var/cache/apk/* \
    && python -m pip install --upgrade pip

COPY . /code/
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "main.py" ]
