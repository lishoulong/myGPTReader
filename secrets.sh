#!/bin/sh

FLY_ENV=$1

if [ -z "$FLY_ENV" ]; then
    echo "Please provide the Fly environment (e.g., production or test)"
    exit 1
fi

if [ "$FLY_ENV" = "production" ]; then
    VERIFICATION_TOKEN_KEY="VERIFICATION_TOKEN_PRODUCTION"
    ENCRYPT_KEY_KEY="ENCRYPT_KEY_PRODUCTION"
    APP_SECRET_KEY="APP_SECRET_PRODUCTION"
    APP_ID_KEY="APP_ID_PRODUCTION"
else
    VERIFICATION_TOKEN_KEY="VERIFICATION_TOKEN_TEST"
    ENCRYPT_KEY_KEY="ENCRYPT_KEY_TEST"
    APP_SECRET_KEY="APP_SECRET_TEST"
    APP_ID_KEY="APP_ID_TEST"
fi

fly secrets set \
    ENVIRONMENT="$FLY_ENV" \
    $VERIFICATION_TOKEN_KEY=IvRAjdCLc1fnuGQWfXWNddiuAbVKdDT1 \
    $ENCRYPT_KEY_KEY= \
    $APP_SECRET_KEY=F0p9FocCRjtCvLfOpTK1ldFvClfw0pBC \
    $APP_ID_KEY=cli_a4ab36b88cf85013 \