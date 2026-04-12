import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

const ERAS = [
    { start: '1956-03-20', end: '1987-11-07', label: 'Bourguiba', color: '#ffefef' },
    { start: '1987-11-07', end: '2011-01-14', label: 'Ben Ali', color: '#eef6ff' },
    { start: '2011-01-14', end: '2014-12-31', label: 'Transition', color: '#f0fff0' },
    { start: '2014-12-31', end: '2019-10-13', label: 'Beji Era', color: '#fff9e6' },
    { start: '2019-10-13', end: '2021-07-25', label: 'Saied Era (Pre-E)', color: '#f5f5f5' },
    { start: '2021-07-25', end: '2026-01-01', label: 'Saied Era (New Const)', color: '#e0e0e0' },
];

const TimelineChart = ({ events, onScrub, currentDate }) => {
    const svgRef = useRef();
    const [width, setWidth] = useState(800);
    const height = 400;
    const margin = { top: 20, right: 30, bottom: 40, left: 150 };

    useEffect(() => {
        const handleResize = () => setWidth(svgRef.current.parentElement.clientWidth);
        window.addEventListener('resize', handleResize);
        handleResize();
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        if (!width) return;
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const x = d3.scaleTime()
            .domain([new Date('1956-01-01'), new Date()])
            .range([margin.left, width - margin.right]);

        // Draw Eras
        svg.selectAll('.era')
            .data(ERAS)
            .enter()
            .append('rect')
            .attr('x', d => x(new Date(d.start)))
            .attr('y', margin.top)
            .attr('width', d => x(new Date(d.end)) - x(new Date(d.start)))
            .attr('height', height - margin.top - margin.bottom)
            .attr('fill', d => d.color)
            .attr('opacity', 0.5);

        svg.selectAll('.era-label')
            .data(ERAS)
            .enter()
            .append('text')
            .attr('x', d => x(new Date(d.start)) + 5)
            .attr('y', height - margin.bottom + 15)
            .text(d => d.label)
            .style('font-size', '10px')
            .style('fill', '#666');

        // Axis
        svg.append('g')
            .attr('transform', `translate(0,${height - margin.bottom})`)
            .call(d3.axisBottom(x));

        // Scrubber (Draggable Date Handle)
        const scrubber = svg.append('line')
            .attr('x1', x(new Date(currentDate)))
            .attr('x2', x(new Date(currentDate)))
            .attr('y1', margin.top)
            .attr('y2', height - margin.bottom)
            .attr('stroke', 'red')
            .attr('stroke-width', 2)
            .style('cursor', 'ew-resize');

        const drag = d3.drag()
            .on('drag', (event) => {
                const newX = Math.max(margin.left, Math.min(event.x, width - margin.right));
                scrubber.attr('x1', newX).attr('x2', newX);
                const newDate = x.invert(newX);
                onScrub(newDate.toISOString().split('T')[0]);
            });

        scrubber.call(drag);

    }, [width, events, onScrub, currentDate]);

    return (
        <div style={{ width: '100%', overflow: 'hidden' }}>
            <svg ref={svgRef} width={width} height={height}></svg>
        </div>
    );
};

export default TimelineChart;
