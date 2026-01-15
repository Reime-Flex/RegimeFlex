'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import { motion } from 'framer-motion';

interface Bar {
    t: string;
    o: number;
    h: number;
    l: number;
    c: number;
    v: number;
}

interface PriceChartProps {
    symbol: string;
    backendUrl: string;
}

const TIMEFRAMES = [
    { label: '1m', value: '1Min' },
    { label: '5m', value: '5Min' },
    { label: '15m', value: '15Min' },
    { label: '1H', value: '1Hour' },
    { label: '1D', value: '1Day' },
];

export const PriceChart: React.FC<PriceChartProps> = ({ symbol, backendUrl }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const candlestickSeriesRef = useRef<ISeriesApi<any> | null>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const volumeSeriesRef = useRef<ISeriesApi<any> | null>(null);

    const [timeframe, setTimeframe] = useState('5Min');
    const [lastPrice, setLastPrice] = useState<number | null>(null);
    const [priceChange, setPriceChange] = useState<{ value: number; percent: number } | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    const fetchBars = useCallback(async () => {
        try {
            const response = await fetch(`${backendUrl}/bars?symbol=${symbol}&tf=${timeframe}&limit=200`);
            if (!response.ok) return null;
            const data = await response.json();
            return data.bars as Bar[];
        } catch (error) {
            console.error('Error fetching bars:', error);
            return null;
        }
    }, [symbol, timeframe, backendUrl]);

    const transformBars = (bars: Bar[]): CandlestickData<Time>[] => {
        return bars.map(bar => ({
            time: (new Date(bar.t).getTime() / 1000) as Time,
            open: bar.o,
            high: bar.h,
            low: bar.l,
            close: bar.c,
        }));
    };

    const transformVolume = (bars: Bar[]) => {
        return bars.map(bar => ({
            time: (new Date(bar.t).getTime() / 1000) as Time,
            value: bar.v,
            color: bar.c >= bar.o ? 'rgba(34, 197, 94, 0.5)' : 'rgba(239, 68, 68, 0.5)',
        }));
    };

    // Initialize chart
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { color: 'transparent' },
                textColor: 'rgba(255, 255, 255, 0.7)',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            crosshair: {
                mode: 1,
                vertLine: {
                    color: 'rgba(255, 255, 255, 0.3)',
                    width: 1,
                    style: 2,
                },
                horzLine: {
                    color: 'rgba(255, 255, 255, 0.3)',
                    width: 1,
                    style: 2,
                },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                timeVisible: true,
                secondsVisible: false,
            },
            handleScroll: {
                vertTouchDrag: false,
            },
        });

        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#22c55e',
            downColor: '#ef4444',
            borderUpColor: '#22c55e',
            borderDownColor: '#ef4444',
            wickUpColor: '#22c55e',
            wickDownColor: '#ef4444',
        });

        const volumeSeries = chart.addSeries(HistogramSeries, {
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        });

        volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });

        chartRef.current = chart;
        candlestickSeriesRef.current = candlestickSeries;
        volumeSeriesRef.current = volumeSeries;

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({
                    width: chartContainerRef.current.clientWidth,
                    height: chartContainerRef.current.clientHeight,
                });
            }
        };

        window.addEventListener('resize', handleResize);
        handleResize();

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    // Fetch and update data
    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            const bars = await fetchBars();

            if (bars && bars.length > 0 && candlestickSeriesRef.current && volumeSeriesRef.current) {
                const candleData = transformBars(bars);
                const volumeData = transformVolume(bars);

                candlestickSeriesRef.current.setData(candleData);
                volumeSeriesRef.current.setData(volumeData);

                // Calculate price change
                const latest = bars[bars.length - 1];
                const first = bars[0];
                setLastPrice(latest.c);
                setPriceChange({
                    value: latest.c - first.o,
                    percent: ((latest.c - first.o) / first.o) * 100,
                });

                chartRef.current?.timeScale().fitContent();
            }
            setIsLoading(false);
        };

        loadData();

        // Refresh data periodically
        const interval = setInterval(loadData, 30000);
        return () => clearInterval(interval);
    }, [fetchBars, timeframe]);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel rounded-xl border border-white/10 overflow-hidden"
        >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/5">
                <div className="flex items-center gap-4">
                    <div>
                        <h3 className="text-lg font-bold">{symbol}</h3>
                        {lastPrice && (
                            <div className="flex items-center gap-2">
                                <span className="text-xl font-mono">${lastPrice.toFixed(2)}</span>
                                {priceChange && (
                                    <span className={`text-sm font-mono ${priceChange.value >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                        {priceChange.value >= 0 ? '+' : ''}{priceChange.value.toFixed(2)} ({priceChange.percent.toFixed(2)}%)
                                    </span>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Timeframe selector */}
                <div className="flex gap-1 bg-white/5 rounded-lg p-1">
                    {TIMEFRAMES.map((tf) => (
                        <button
                            key={tf.value}
                            onClick={() => setTimeframe(tf.value)}
                            className={`px-3 py-1 rounded text-sm font-mono transition-colors ${
                                timeframe === tf.value
                                    ? 'bg-white/20 text-white'
                                    : 'text-white/50 hover:text-white/80'
                            }`}
                        >
                            {tf.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Chart container */}
            <div className="relative" style={{ height: '400px' }}>
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/20 z-10">
                        <div className="animate-pulse text-white/50">Loading chart...</div>
                    </div>
                )}
                <div ref={chartContainerRef} className="w-full h-full" />
            </div>
        </motion.div>
    );
};
