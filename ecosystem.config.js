/**
 * PM2 Ecosystem Configuration for RegimeFlex
 * 
 * This configuration ensures the trading bot runs reliably with:
 * - Automatic restarts on crash
 * - Exponential backoff on repeated failures
 * - Memory limits
 * - Separate watchdog process
 * 
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 start ecosystem.config.js --env paper  # Paper trading mode
 *   pm2 logs regimeflex
 *   pm2 status
 */
module.exports = {
    apps: [
        // Main RegimeFlex trading bot
        {
            name: "regimeflex",
            script: "python",
            args: "regimeflex/scripts/trigger_server.py",
            cwd: "./",

            // Instance management
            instances: 1,
            exec_mode: "fork",

            // Restart behavior - instant restart on crash
            autorestart: true,
            watch: false,
            max_restarts: 50,                        // Allow more restarts before giving up
            min_uptime: "5s",                       // Consider stable after 5 seconds
            restart_delay: 0,                        // Instant restart (no delay)
            exp_backoff_restart_delay: 0,           // No exponential backoff for instant restart
            max_memory_restart: "1G",               // Restart if memory exceeds 1GB
            kill_timeout: 5000,                     // 5 second grace period for shutdown

            // Resource limits
            max_memory_restart: "1G",

            // Logging
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            error_file: "./logs/pm2-error.log",
            out_file: "./logs/pm2-out.log",
            merge_logs: true,

            // Environment variables - Production
            env: {
                NODE_ENV: "production",
                REGIMEFLEX_DRY_RUN: "0",
                PYTHONUNBUFFERED: "1"
            },

            // Environment variables - Paper trading
            env_paper: {
                NODE_ENV: "development",
                REGIMEFLEX_DRY_RUN: "1",
                PYTHONUNBUFFERED: "1"
            },

            // Environment variables - Development
            env_development: {
                NODE_ENV: "development",
                REGIMEFLEX_DRY_RUN: "1",
                PYTHONUNBUFFERED: "1"
            }
        },

        // Guardian Watchdog process
        {
            name: "regimeflex-watchdog",
            script: "python",
            args: "regimeflex/scripts/watchdog_monitor.py",
            cwd: "./",

            // Instance management
            instances: 1,
            exec_mode: "fork",

            // Restart behavior - watchdog should always be running
            autorestart: true,
            watch: false,
            max_restarts: -1,           // Unlimited restarts for watchdog
            min_uptime: "5s",
            restart_delay: 10000,       // 10 second delay

            // Logging
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            error_file: "./logs/pm2-watchdog-error.log",
            out_file: "./logs/pm2-watchdog-out.log",
            merge_logs: true,

            // Environment
            env: {
                NODE_ENV: "production",
                PYTHONUNBUFFERED: "1"
            }
        },

        // Scheduled heartbeat sender (runs every 4 hours via cron)
        {
            name: "regimeflex-heartbeat",
            script: "python",
            args: "regimeflex/scripts/send_heartbeat.py",
            cwd: "./",

            // Cron: every 4 hours
            cron_restart: "0 */4 * * *",
            autorestart: false,         // Don't auto-restart between cron runs

            // Logging
            log_date_format: "YYYY-MM-DD HH:mm:ss Z",
            error_file: "./logs/pm2-heartbeat-error.log",
            out_file: "./logs/pm2-heartbeat-out.log",
            merge_logs: true,

            // Environment
            env: {
                NODE_ENV: "production",
                PYTHONUNBUFFERED: "1"
            }
        }
    ]
};
