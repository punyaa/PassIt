# Thumbnail Lambda, invoked by S3 when a listing photo is uploaded.
# Handler: handler.handler
# Build: docker build --platform linux/arm64 --provenance=false infra/lambdas/thumbnailer
FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.handler"]
