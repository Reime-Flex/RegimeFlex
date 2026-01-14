module.exports = {
  apps: [
    {
      name: 'regimeflex-http',
      script: 'python',
      args: '-m regimeflex http',
      cwd: '/Users/abuaa/Projects/RegimeFlex',
      interpreter: '/Users/abuaa/Projects/RegimeFlex/.venv/bin/python',
      env: {
        PORT: 8080,
        ENV: 'dev'
      },
      env_production: {
        PORT: 8080,
        ENV: 'prod'
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000
    },
    {
      name: 'regimeflex-web',
      script: 'npm',
      args: 'run start',
      cwd: '/Users/abuaa/Projects/RegimeFlex/web',
      env: {
        PORT: 3000,
        PYTHON_BACKEND_URL: 'http://localhost:8080'
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000
    }
  ]
};
