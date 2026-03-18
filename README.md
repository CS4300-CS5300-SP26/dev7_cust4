# dev7_cust4
Group project repo — dev7 → cust4

## Website Link: https://cinelog-service-production.up.railway.app/

## AI Usage: 

Claude was used on production deployment for debug help as well as asking questions and doing research on potential solutions.
Claude was used for creating unit testing for movies_view and movie_detail_view.
ChatGPT was used to explain how to use git pull request, resolve conflicts, and merge and explain any errors. Also used to debug. 
PardotAI was used to help assist with AI code review. 
## Railway setup information:

### Install Railway CLI:

npm install @railway/cli


### Login and create project:

npx railway login (For me, using DevEdu, I had to include --browserless to login)
npx railway init


### Add Postgres database. It should automatically link to your project:

npx railway add --database postgres


### Set environment variables:

npx railway variables set SECRET_KEY=yoursecretkey

npx railway variables set DJANGO_SETTINGS_MODULE=cinelog.settings

npx railway variables set DJANGO_SETTINGS_MODULE=cinelog.settings

npx railway variables set TMDB_API_KEY=yourtmdbkey

npx railway variables set OMBD_API_KEY=yourombdkey


### Generate a public URL:

npx railway domain


### Then add that URL to settings.py:

pythonALLOWED_HOSTS = ['.railway.app', 'your-url.railway.app']

CSRF_TRUSTED_ORIGINS = ['https://your-url.railway.app']

### Deploy:

npx railway up

### Run migrations after first deploy:

npx railway run python manage.py migrate
