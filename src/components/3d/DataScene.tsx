"use client";

import { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useAppStore } from '@/lib/store';
import { EffectComposer, Bloom, DepthOfField } from '@react-three/postprocessing';
import type { BloomEffect } from 'postprocessing';

const PARTICLE_COUNT = 3000;

export default function DataScene() {
    const pointsRef = useRef<THREE.Points>(null);
    const bloomRef = useRef<BloomEffect>(null);
    const isProcessing = useAppStore((s) => s.isProcessing);
    const isDashboard = useAppStore((s) => s.isDashboard);
    const highlightParticles = useAppStore((s) => s.highlightParticles);
    const { pointer } = useThree();

    // 1. Particle Shape: Circular Alpha Map
    const circleTexture = useMemo(() => {
        const canvas = document.createElement('canvas');
        canvas.width = 64;
        canvas.height = 64;
        const context = canvas.getContext('2d')!;
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = canvas.width / 2;
        
        // Soft gradient for a glowing orb effect
        const gradient = context.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
        gradient.addColorStop(0, 'rgba(255,255,255,1)');
        gradient.addColorStop(0.2, 'rgba(255,255,255,0.8)');
        gradient.addColorStop(1, 'rgba(255,255,255,0)');
        
        context.fillStyle = gradient;
        context.fillRect(0, 0, canvas.width, canvas.height);
        
        const texture = new THREE.CanvasTexture(canvas);
        texture.premultiplyAlpha = true;
        return texture;
    }, []);

    const { idlePositions, processingPositions, colors, randomOffsets } = useMemo(() => {
        const idle = new Float32Array(PARTICLE_COUNT * 3);
        const grid = new Float32Array(PARTICLE_COUNT * 3);
        const cols = new Float32Array(PARTICLE_COUNT * 3);
        const randOffsets = new Float32Array(PARTICLE_COUNT);

        const gridSize = Math.ceil(Math.pow(PARTICLE_COUNT, 1 / 3));
        const step = 0.5;
        const offset = (gridSize * step) / 2;

        const colorCyan = new THREE.Color('#06b6d4');
        const colorPurple = new THREE.Color('#a855f7');
        const tempColor = new THREE.Color();

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            // Idle: galaxy sphere
            const radius = 2 + Math.random() * 5;
            const theta = Math.random() * 2 * Math.PI;
            const phi = Math.acos((Math.random() * 2) - 1);
            
            const ix = radius * Math.sin(phi) * Math.cos(theta);
            const iy = radius * Math.sin(phi) * Math.sin(theta);
            const iz = radius * Math.cos(phi);
            
            idle[i * 3]     = ix;
            idle[i * 3 + 1] = iy;
            idle[i * 3 + 2] = iz;

            // Processing: neural network lattice
            const gx = (i % gridSize) * step - offset;
            const gy = (Math.floor(i / gridSize) % gridSize) * step - offset;
            const gz = (Math.floor(i / (gridSize * gridSize))) * step - offset;
            grid[i * 3]     = gx + (Math.random() * 0.1 - 0.05);
            grid[i * 3 + 1] = gy + (Math.random() * 0.1 - 0.05);
            grid[i * 3 + 2] = gz + (Math.random() * 0.1 - 0.05);
            
            // Random offset for organic wave movement
            randOffsets[i] = Math.random() * Math.PI * 2;

            // Gradient Colors based on X position
            // Map X broadly between -5 and 5 to a 0-1 lerp value
            const normalizedX = Math.max(0, Math.min(1, (ix + 5) / 10));
            tempColor.lerpColors(colorCyan, colorPurple, normalizedX);
            cols[i * 3] = tempColor.r;
            cols[i * 3 + 1] = tempColor.g;
            cols[i * 3 + 2] = tempColor.b;
        }

        return { idlePositions: idle, processingPositions: grid, colors: cols, randomOffsets: randOffsets };
    }, []);

    const geometry = useMemo(() => {
        const geo = new THREE.BufferGeometry();
        // We use idlePositions as the base buffer, but it gets overwritten every frame anyway
        geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(idlePositions), 3));
        geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        return geo;
    }, [idlePositions, colors]);

    useFrame((state, delta) => {
        if (!pointsRef.current) return;

        const wantLattice = isProcessing && !isDashboard;
        const targetPositions = wantLattice ? processingPositions : idlePositions;
        const positions = pointsRef.current.geometry.attributes.position.array as Float32Array;
        
        const time = state.clock.elapsedTime;
        
        // Mouse coordinates for repulsion (-5 to +5 range roughly)
        const mouseX = pointer.x * 5; 
        const mouseY = pointer.y * 5;

        const lerpSpeed = wantLattice ? delta * 4 : delta * 0.5;

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const idx = i * 3;
            
            // Base target
            let tx = targetPositions[idx];
            let ty = targetPositions[idx + 1];
            let tz = targetPositions[idx + 2];

            // 3. Fluid Wave Motion (when not forming rigid lattice)
            if (!wantLattice) {
                const wave = Math.sin(time * 0.5 + targetPositions[idx] + randomOffsets[i]) * 0.2;
                ty += wave;
                tx += Math.cos(time * 0.3 + targetPositions[idx+1]) * 0.1;
            }

            // 5. Mouse Repulsion Force
            if (!wantLattice) {
                // Approximate un-rotated position 
                // (Very simplified repulsion ignoring object rotation for performance)
                const dx = tx - mouseX;
                const dy = ty - mouseY;
                const distSq = dx * dx + dy * dy;
                
                if (distSq < 4) { // Repulsion radius
                    const force = (4 - distSq) * 0.2;
                    tx += (dx / Math.sqrt(distSq)) * force;
                    ty += (dy / Math.sqrt(distSq)) * force;
                }
            }

            // Move current towards target
            positions[idx] += (tx - positions[idx]) * lerpSpeed;
            positions[idx + 1] += (ty - positions[idx + 1]) * lerpSpeed;
            positions[idx + 2] += (tz - positions[idx + 2]) * lerpSpeed;
        }
        
        pointsRef.current.geometry.attributes.position.needsUpdate = true;

        // Lerp Bloom intensity: higher when hovering a story card
        if (bloomRef.current) {
            const baseIntensity = isDashboard ? 1.5 : 0.6;
            const targetIntensity = highlightParticles ? 2.8 : baseIntensity;
            bloomRef.current.intensity = THREE.MathUtils.lerp(bloomRef.current.intensity, targetIntensity, delta * 3);
        }

        if (wantLattice) {
            pointsRef.current.rotation.y = THREE.MathUtils.lerp(pointsRef.current.rotation.y, 0, delta * 2);
            pointsRef.current.rotation.x = THREE.MathUtils.lerp(pointsRef.current.rotation.x, 0, delta * 2);
        } else {
            pointsRef.current.rotation.y += delta * 0.05;
            pointsRef.current.rotation.x += delta * 0.02;
        }
    });

    return (
        <>
            <points ref={pointsRef} geometry={geometry}>
                <pointsMaterial
                    size={0.12}
                    vertexColors={true}
                    transparent
                    opacity={0.8}
                    alphaMap={circleTexture}
                    alphaTest={0.01}
                    sizeAttenuation
                    blending={THREE.AdditiveBlending}
                    depthWrite={false}
                />
            </points>
            
            {/* 1. Cinematic Post-Processing */}
            <EffectComposer multisampling={4}>
                <DepthOfField 
                    focusDistance={0.05} 
                    focalLength={0.1} 
                    bokehScale={2} 
                    height={480} 
                />
                <Bloom 
                    ref={bloomRef}
                    luminanceThreshold={0.2} 
                    luminanceSmoothing={0.9} 
                    intensity={1.5} 
                    mipmapBlur 
                />
            </EffectComposer>
        </>
    );
}
