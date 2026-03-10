"use client";

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useAppStore } from '@/lib/store';

const PARTICLE_COUNT = 2000;

export default function DataScene() {
    const pointsRef = useRef<THREE.Points>(null);
    const isProcessing = useAppStore((s) => s.isProcessing);
    const isDashboard = useAppStore((s) => s.isDashboard);

    const { idlePositions, processingPositions } = useMemo(() => {
        const idle = new Float32Array(PARTICLE_COUNT * 3);
        const grid = new Float32Array(PARTICLE_COUNT * 3);

        const gridSize = Math.ceil(Math.pow(PARTICLE_COUNT, 1 / 3));
        const step = 0.5;
        const offset = (gridSize * step) / 2;

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            // Idle: random galaxy sphere
            const radius = 2 + Math.random() * 5;
            const theta = Math.random() * 2 * Math.PI;
            const phi = Math.acos((Math.random() * 2) - 1);
            idle[i * 3]     = radius * Math.sin(phi) * Math.cos(theta);
            idle[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
            idle[i * 3 + 2] = radius * Math.cos(phi);

            // Processing: neural network lattice
            const gx = (i % gridSize) * step - offset;
            const gy = (Math.floor(i / gridSize) % gridSize) * step - offset;
            const gz = (Math.floor(i / (gridSize * gridSize))) * step - offset;
            grid[i * 3]     = gx + (Math.random() * 0.1 - 0.05);
            grid[i * 3 + 1] = gy + (Math.random() * 0.1 - 0.05);
            grid[i * 3 + 2] = gz + (Math.random() * 0.1 - 0.05);
        }

        return { idlePositions: idle, processingPositions: grid };
    }, []);

    const geometry = useMemo(() => {
        const geo = new THREE.BufferGeometry();
        // Start in idle positions
        geo.setAttribute('position', new THREE.BufferAttribute(idlePositions.slice(), 3));
        return geo;
    }, [idlePositions]);

    useFrame((_, delta) => {
        if (!pointsRef.current) return;

        // Processing-only = lattice; idle or dashboard = galaxy
        const wantLattice = isProcessing && !isDashboard;
        const targetPositions = wantLattice ? processingPositions : idlePositions;
        const current = pointsRef.current.geometry.attributes.position.array as Float32Array;

        // Lerp at 4× speed so the shift is unmissably visible (~0.5 s to settle)
        const lerpFactor = Math.min(delta * 4, 0.15);
        let needsUpdate = false;
        for (let i = 0; i < current.length; i++) {
            const diff = targetPositions[i] - current[i];
            if (Math.abs(diff) > 0.001) {
                current[i] += diff * lerpFactor;
                needsUpdate = true;
            }
        }
        if (needsUpdate) {
            pointsRef.current.geometry.attributes.position.needsUpdate = true;
        }

        // Rotation: galaxy drifts freely; lattice aligns to center;
        // dashboard returns to slow galaxy drift
        if (wantLattice) {
            pointsRef.current.rotation.y = THREE.MathUtils.lerp(
                pointsRef.current.rotation.y, 0, delta * 2
            );
            pointsRef.current.rotation.x = THREE.MathUtils.lerp(
                pointsRef.current.rotation.x, 0, delta * 2
            );
        } else {
            pointsRef.current.rotation.y += delta * 0.05;
            pointsRef.current.rotation.x += delta * 0.02;
        }
    });

    return (
        <points ref={pointsRef} geometry={geometry}>
            <pointsMaterial
                size={0.05}
                color={isProcessing && !isDashboard ? '#a855f7' : '#06b6d4'}
                transparent
                opacity={0.8}
                sizeAttenuation
                blending={THREE.AdditiveBlending}
                depthWrite={false}
            />
        </points>
    );
}
