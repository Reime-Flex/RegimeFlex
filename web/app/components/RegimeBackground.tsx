'use client';

import React from 'react';
import { useRegime } from '../context/RegimeContext';
import { motion } from 'framer-motion';

export const RegimeBackground = () => {
    const { regime } = useRegime();

    const getGradient = () => {
        switch (regime) {
            case 'BULL':
                return 'radial-gradient(circle at 50% 0%, #064e3b 0%, #022c22 40%, #0f172a 100%)';
            case 'BEAR':
                return 'radial-gradient(circle at 50% 0%, #7f1d1d 0%, #450a0a 40%, #0f172a 100%)';
            case 'NEUTRAL':
            default:
                return 'radial-gradient(circle at 50% 0%, #334155 0%, #1e293b 40%, #0f172a 100%)';
        }
    };

    return (
        <motion.div
            className="fixed inset-0 -z-10 w-full h-full pointer-events-none"
            initial={false}
            animate={{
                background: getGradient(),
            }}
            transition={{ duration: 1.5, ease: "easeInOut" }}
        />
    );
};
