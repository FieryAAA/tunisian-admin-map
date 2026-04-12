import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import dagre from 'dagre';

const OrgChart = ({ data }) => {
    const svgRef = useRef();
    const [width, setWidth] = useState(600);
    const height = 500;

    useEffect(() => {
        const handleResize = () => setWidth(svgRef.current.parentElement.clientWidth);
        window.addEventListener('resize', handleResize);
        handleResize();
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    useEffect(() => {
        if (!width || !data || !data.institutions) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const g = new dagre.graphlib.Graph();
        g.setGraph({ rankdir: 'LR', nodesep: 50, ranksep: 100 });
        g.setDefaultEdgeLabel(() => ({}));

        // Add Nodes
        data.institutions.forEach(inst => {
            g.setNode(inst.id, { 
                label: inst.name_fr, 
                width: 150, 
                height: 50,
                type: inst.type,
                person: inst.person ? inst.person.name_fr : null
            });
        });

        // Add Edges
        data.institutions.forEach(inst => {
            if (inst.parent_id) {
                g.setEdge(inst.parent_id, inst.id);
            }
        });

        dagre.layout(g);

        // Rendering
        const mainG = svg.append('g').attr('transform', 'translate(20,20)');

        // Draw Links
        g.edges().forEach((e) => {
            const edge = g.edge(e);
            mainG.append('path')
                .attr('d', d3.line().curve(d3.curveBasis)([
                    [edge.points[0].x, edge.points[0].y],
                    ...edge.points.map(p => [p.x, p.y]),
                    [edge.points[edge.points.length-1].x, edge.points[edge.points.length-1].y]
                ]))
                .attr('fill', 'none')
                .attr('stroke', '#ccc')
                .attr('stroke-width', 2);
        });

        // Draw Nodes
        g.nodes().forEach((v) => {
            const node = g.node(v);
            const nodeG = mainG.append('g')
                .attr('transform', `translate(${node.x - node.width/2},${node.y - node.height/2})`);

            nodeG.append('rect')
                .attr('width', node.width)
                .attr('height', node.height)
                .attr('rx', 5)
                .attr('fill', '#fff')
                .attr('stroke', node.type === 'ministry' ? '#2563eb' : '#64748b')
                .attr('stroke-width', 2);

            nodeG.append('text')
                .attr('x', 10)
                .attr('y', 20)
                .text(node.label)
                .style('font-size', '10px')
                .style('font-weight', 'bold');

            if (node.person) {
                nodeG.append('text')
                    .attr('x', 10)
                    .attr('y', 40)
                    .text(node.person)
                    .style('font-size', '9px')
                    .style('fill', '#6b7280');
            }
        });

    }, [width, data]);

    return (
        <div style={{ width: '100%', height: '100%', border: '1px solid #ddd' }}>
            <svg ref={svgRef} width={width} height={height}></svg>
        </div>
    );
};

export default OrgChart;
