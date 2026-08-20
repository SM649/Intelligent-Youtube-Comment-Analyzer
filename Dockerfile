FROM python:3.10-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    MPLCONFIGDIR=/home/user/.config/matplotlib \
    NLTK_DATA=/home/user/nltk_data

WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

ENV PORT=7860
EXPOSE 7860

CMD ["gunicorn", "-w", "1", "-t", "300", "-b", "0.0.0.0:7860", "app:app"]
