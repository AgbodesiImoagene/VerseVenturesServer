FROM public.ecr.aws/lambda/python:3.12

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install the specified packages
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Create and set model cache directory
RUN mkdir -p ${LAMBDA_TASK_ROOT}/model_cache
ENV TRANSFORMERS_CACHE=${LAMBDA_TASK_ROOT}/model_cache
ENV SENTENCE_TRANSFORMERS_HOME=${LAMBDA_TASK_ROOT}/model_cache

# Pre-download the model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler" ]
