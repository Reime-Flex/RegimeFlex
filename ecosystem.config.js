/**
 * PM2 Ecosystem Configuration for RegimeFlex
 * 
 * Production-ready configuration with:
 * - Absolute paths (PM2-safe)
 * - Single process mode (never cluster for trading!)
 * - Virtual environment Python interpreter
 * - Comprehensive logging
 * - Graceful shutdown
 * - Environment variable management
 * 
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 logs regimeflex-trading
 *   pm2 status
 *   pm2 stop regimeflex-trading
 *   pm2 delete regimeflex-trading
 */
module.exports = {
    apps: [
        // Main RegimeFlex trading bot
        {
            name: 'regimeflex-trading',
            script: 'python',
            args: ['-m', 'regimeflex', 'run'],
            
            // Use absolute path or environment variable
            cwd: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
            
            // Use Python from virtual environment
            interpreter: '.venv/bin/python',
            interpreter_args: '',
            
            // Single instance (never cluster for trading!)
            instances: 1,
            exec_mode: 'fork',
            
            // Restart behavior
            autorestart: true,
            max_restarts: 10,              // Limit restarts to prevent infinite loops
            min_uptime: 60000,            // 60 seconds - consider stable after this
            restart_delay: 5000,          // 5 seconds between restarts
            exp_backoff_restart_delay: 100,  // Exponential backoff base (ms)
            max_memory_restart: '1G',     // Restart if memory exceeds 1GB
            
            // Logging (absolute paths)
            error_file: './logs/pm2-error.log',
            out_file: './logs/pm2-out.log',
            log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
            merge_logs: true,
            log_type: 'json',             // JSON logs for easier parsing
            
            // Environment variables
            env: {
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                ENV: 'prod',
                NODE_ENV: 'production',
                PYTHONUNBUFFERED: '1',     // Unbuffered output for real-time logs
                REGIMEFLEX_DRY_RUN: '0'    // Live trading mode
            },
            
            // Paper trading environment
            env_paper: {
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                ENV: 'dev',
                NODE_ENV: 'development',
                PYTHONUNBUFFERED: '1',
                REGIMEFLEX_DRY_RUN: '1'    // Paper trading mode
            },
            
            // Development environment
            env_development: {
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                ENV: 'dev',
                NODE_ENV: 'development',
                PYTHONUNBUFFERED: '1',
                REGIMEFLEX_DRY_RUN: '1'
            },
            
            // Watch disabled (not needed for scheduled runs)
            watch: false,
            
            // Graceful shutdown
            kill_timeout: 10000,          // 10 seconds for graceful shutdown
            wait_ready: false,            // Don't wait for ready signal
            listen_timeout: 3000,         // 3 seconds timeout for listen
            
            // Instance vars (shared across restarts)
            instance_var: {
                'REGIMEFLEX_STARTED_AT': new Date().toISOString()
            }
        },
        
        // Guardian Watchdog process
        {
            name: 'regimeflex-watchdog',
            script: 'python',
            args: ['-m', 'regimeflex.scripts.watchdog_monitor'],
            
            cwd: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
            interpreter: '.venv/bin/python',
            
            instances: 1,
            exec_mode: 'fork',
            
            // Watchdog should always be running
            autorestart: true,
            max_restarts: -1,             // Unlimited restarts for watchdog
            min_uptime: 5000,             // 5 seconds
            restart_delay: 10000,         // 10 second delay
            
            // Logging
            error_file: './logs/pm2-watchdog-error.log',
            out_file: './logs/pm2-watchdog-out.log',
            log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
            merge_logs: true,
            
            // Environment
            env: {
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                ENV: 'prod',
                NODE_ENV: 'production',
                PYTHONUNBUFFERED: '1'
            },
            
            watch: false,
            kill_timeout: 5000
        },
        
        // HTTP Trigger Server (for Railway/cron)
        {
            name: 'regimeflex-http',
            script: 'python',
            args: ['-m', 'regimeflex', 'http'],
            
            cwd: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
            interpreter: '.venv/bin/python',
            
            instances: 1,
            exec_mode: 'fork',
            
            autorestart: true,
            max_restarts: 10,
            min_uptime: 30000,            // 30 seconds
            restart_delay: 5000,
            
            // Logging
            error_file: './logs/pm2-http-error.log',
            out_file: './logs/pm2-http-out.log',
            log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
            merge_logs: true,
            
            // Environment
            env: {
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                ENV: 'prod',
                NODE_ENV: 'production',
                PYTHONUNBUFFERED: '1',
                PORT: process.env.PORT || '5000'
            },
            
            watch: false,
            kill_timeout: 10000
        }
    ]
};
