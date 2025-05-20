# TechTranslator Frontend

This is the frontend for the TechTranslator application, which provides explanations of data science and machine learning concepts for insurance professionals.

## Structure

- `public/`: Contains HTML files and static assets that are directly served
- `src/`: Contains source code
  - `css/`: Stylesheets
  - `js/`: JavaScript files
  - `assets/`: Images and other assets

## Setup

1. Update the API URL in `src/js/api.js` with your deployed API Gateway URL
2. Update the Cognito parameters in `src/js/auth.js` with your Cognito User Pool ID and Client ID
3. Add a favicon.ico to the public directory

## Deployment

Use the `upload-frontend.sh` script to deploy the frontend to the S3 bucket.