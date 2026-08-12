FROM python:3.11-slim

WORKDIR /code

# AWS infrastructure is operated from this project's own workbench. Install
# the same digest-pinned CLI used by CI for both Womb's arm64 development
# containers and GitHub's x64 runners; credentials remain runtime-only.
COPY .aws-cli-version /tmp/henry-tooling/.aws-cli-version
COPY scripts/install_aws_cli.py /tmp/henry-tooling/scripts/install_aws_cli.py
RUN python3 /tmp/henry-tooling/scripts/install_aws_cli.py \
      --install-root /opt/aws-cli \
      --bin-dir /usr/local/bin \
    && rm -rf /tmp/henry-tooling

ENV AWS_PAGER="" \
    AWS_CLI_AUTO_PROMPT=off

CMD ["sleep", "infinity"]
