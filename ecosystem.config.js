/**
 * PM2 Ecosystem Configuration for RegimeFlex Trading System
 * 
 * ==========================================
 * PRODUCTION DEPLOYMENT CONFIGURATION
 * ==========================================
 * 
 * This configuration ensures RegimeFlex runs correctly in production
 * environments where PM2 may change the working directory.
 * 
 * Key Features:
 * - Absolute paths (works from any directory)
 * - Single process mode (CRITICAL for trading)
 * - Virtual environment Python interpreter
 * - Comprehensive logging
 * - Graceful shutdown handling
 * - Environment variable management
 * 
 * Usage:
 *   # Start all processes
 *   pm2 start ecosystem.config.js
 *   
 *   # Start specific process
 *   pm2 start ecosystem.config.js --only regimeflex-trading
 *   
 *   # View logs
 *   pm2 logs regimeflex-trading
 *   pm2 logs regimeflex-watchdog
 *   pm2 logs regimeflex-http
 *   
 *   # Check status
 *   pm2 status
 *   
 *   # Stop/restart
 *   pm2 stop regimeflex-trading
 *   pm2 restart regimeflex-trading
 *   pm2 delete regimeflex-trading
 * 
 * Environment Variables:
 *   REGIMEFLEX_ROOT - Project root directory (defaults to /home/user/RegimeFlex)
 *   PORT - HTTP server port (defaults to 5000)
 */
module.exports = {
    apps: [
        // ==========================================
        // Main RegimeFlex Trading Bot
        // ==========================================
        {
            name: 'regimeflex-trading',
            
            // ==========================================
            // Execution Configuration
            // ==========================================
            // Use 'python' command (PM2 will find it in PATH)
            // For virtual environment, set interpreter to venv path
            script: 'python',
            args: ['-m', 'regimeflex', 'run'],
            
            // Working directory (CRITICAL for absolute paths)
            // Set REGIMEFLEX_ROOT env var or use default path
            // With Phase 2 path absolutization, this can be any directory,
            // but setting it to project root is still recommended
            cwd: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
            
            // Python interpreter
            // Option 1: Use 'none' and let system PATH find python
            // Option 2: Use full path to venv python (recommended for production)
            // Option 3: Use 'python3' if python3 is in PATH
            interpreter: process.env.PYTHON_INTERPRETER || '.venv/bin/python',
            interpreter_args: '',
            
            // ==========================================
            // CRITICAL: Single Instance Only
            // ==========================================
            // ⚠️  WARNING: Trading systems MUST NEVER run concurrently!
            // Multiple instances = duplicate orders = financial disaster
            // NEVER set instances > 1 for trading systems
            instances: 1,
            exec_mode: 'fork',  // NOT 'cluster' - fork mode for single process
            
            // ==========================================
            // Restart Behavior
            // ==========================================
            autorestart: true,              // Restart on crash
            max_restarts: 10,               // Stop restarting after 10 crashes (prevents infinite loops)
            min_uptime: 60000,              // Must stay up 60s to count as stable restart
            restart_delay: 5000,            // Wait 5 seconds between restart attempts
            exp_backoff_restart_delay: 100, // Exponential backoff base (ms)
            max_memory_restart: '1G',       // Restart if memory exceeds 1GB (safety limit)
            
            // ==========================================
            // Logging Configuration
            // ==========================================
            // Logs are relative to cwd (which is project root)
            // With absolute paths (Phase 2), these will work correctly
            error_file: './logs/pm2-error.log',
            out_file: './logs/pm2-out.log',
            log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
            merge_logs: true,               // Combine logs from restarts
            log_type: 'json',               // JSON logs for easier parsing (optional)
            
            // ==========================================
            // Environment Variables
            // ==========================================
            env: {
                // Python path (for imports)
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                
                // Environment type
                ENV: 'prod',
                NODE_ENV: 'production',
                
                // Python output (unbuffered for real-time logs)
                PYTHONUNBUFFERED: '1',
                
                // Trading mode (0 = live, 1 = paper/dry-run)
                REGIMEFLEX_DRY_RUN: '0'
            },
            
            // ==========================================
            // Paper Trading Environment
            // ==========================================
            // Use: pm2 start ecosystem.config.js --env env_paper
            env_paper: {
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                ENV: 'dev',
                NODE_ENV: 'development',
                PYTHONUNBUFFERED: '1',
                REGIMEFLEX_DRY_RUN: '1'     // Paper trading mode
            },
            
            // ==========================================
            // Development Environment
            // ==========================================
            // Use: pm2 start ecosystem.config.js --env env_development
            env_development: {
                PYTHONPATH: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
                ENV: 'dev',
                NODE_ENV: 'development',
                PYTHONUNBUFFERED: '1',
                REGIMEFLEX_DRY_RUN: '1'
            },
            
            // ==========================================
            // Watch Mode (Disabled for Production)
            // ==========================================
            // Watch mode is disabled for production
            // Trading systems should run on schedule, not file changes
            watch: false,
            
            // ==========================================
            // Graceful Shutdown
            // ==========================================
            kill_timeout: 10000,            // 10 seconds for cleanup on stop
            wait_ready: false,              // Don't wait for ready signal
            listen_timeout: 3000,           // 3 second timeout for listen
            
            // ==========================================
            // Instance Variables (Shared Across Restarts)
            // ==========================================
            instance_var: {
                'REGIMEFLEX_STARTED_AT': new Date().toISOString()
            }
        },
        
        // ==========================================
        // Guardian Watchdog Process
        // ==========================================
        // Monitors the trading bot and triggers recovery if stale
        {
            name: 'regimeflex-watchdog',
            script: 'python',
            args: ['-m', 'regimeflex.scripts.watchdog_monitor'],
            
            cwd: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
            interpreter: process.env.PYTHON_INTERPRETER || '.venv/bin/python',
            
            // Single instance
            instances: 1,
            exec_mode: 'fork',
            
            // Watchdog should always be running
            autorestart: true,
            max_restarts: -1,               // Unlimited restarts for watchdog (critical service)
            min_uptime: 5000,               // 5 seconds minimum uptime
            restart_delay: 10000,           // 10 second delay between restarts
            
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
        
        // ==========================================
        // HTTP Trigger Server (for Railway/cron)
        // ==========================================
        // Provides HTTP endpoints for triggering trading cycles
        // Used by Railway, cron jobs, or external schedulers
        {
            name: 'regimeflex-http',
            script: 'python',
            args: ['-m', 'regimeflex', 'http'],
            
            cwd: process.env.REGIMEFLEX_ROOT || '/home/user/RegimeFlex',
            interpreter: process.env.PYTHON_INTERPRETER || '.venv/bin/python',
            
            // Single instance
            instances: 1,
            exec_mode: 'fork',
            
            autorestart: true,
            max_restarts: 10,
            min_uptime: 30000,              // 30 seconds minimum uptime
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
                PORT: process.env.PORT || '5000'  // HTTP server port
            },
            
            watch: false,
            kill_timeout: 10000
        }
    ]
};
