import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as THREE from 'three';

function Door() {
  const mountRef = useRef(null);
  const navigate = useNavigate();
  const [zooming, setZooming] = useState(false);
  const zoomingRef = useRef(false);

  useEffect(() => {
    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x05030a, 0.08);

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    camera.position.set(0, 0.6, 8);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(width, height);
    renderer.setClearColor(0x05030a, 1);
    mount.appendChild(renderer.domElement);

    // Ambient mystical light
    const ambient = new THREE.AmbientLight(0x6a4ea8, 0.4);
    scene.add(ambient);

    // Warm glow from inside the doorway
    const doorLight = new THREE.PointLight(0xffb86b, 3, 12, 1.6);
    doorLight.position.set(0, 0.5, -0.4);
    scene.add(doorLight);

    // Cool rim light
    const rimLight = new THREE.PointLight(0x6e8cff, 1.2, 14);
    rimLight.position.set(-4, 4, 4);
    scene.add(rimLight);

    // ----- Door group -----
    const doorGroup = new THREE.Group();
    scene.add(doorGroup);

    // Stone arch frame (built from a torus + rectangles)
    const frameMaterial = new THREE.MeshStandardMaterial({
      color: 0x2a2238,
      roughness: 0.95,
      metalness: 0.1,
      emissive: 0x1a0f2a,
      emissiveIntensity: 0.4,
    });

    const arch = new THREE.Mesh(
      new THREE.TorusGeometry(1.6, 0.18, 16, 48, Math.PI),
      frameMaterial
    );
    arch.position.y = 1.2;
    doorGroup.add(arch);

    const leftPillar = new THREE.Mesh(
      new THREE.BoxGeometry(0.36, 2.6, 0.36),
      frameMaterial
    );
    leftPillar.position.set(-1.6, -0.1, 0);
    doorGroup.add(leftPillar);

    const rightPillar = leftPillar.clone();
    rightPillar.position.x = 1.6;
    doorGroup.add(rightPillar);

    const lintel = new THREE.Mesh(
      new THREE.BoxGeometry(3.6, 0.22, 0.4),
      frameMaterial
    );
    lintel.position.y = -1.4;
    doorGroup.add(lintel);

    // The "portal" inside the arch — a glowing surface that we'll fly through
    const portalGeo = new THREE.PlaneGeometry(2.9, 3.6, 1, 1);
    const portalMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColorA: { value: new THREE.Color(0xffb86b) },
        uColorB: { value: new THREE.Color(0x9a5cff) },
      },
      transparent: true,
      side: THREE.DoubleSide,
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec2 vUv;
        uniform float uTime;
        uniform vec3 uColorA;
        uniform vec3 uColorB;

        // simple swirl noise
        float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        float noise(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          float a = hash(i);
          float b = hash(i + vec2(1.0, 0.0));
          float c = hash(i + vec2(0.0, 1.0));
          float d = hash(i + vec2(1.0, 1.0));
          vec2 u = f * f * (3.0 - 2.0 * f);
          return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
        }

        void main() {
          vec2 uv = vUv - 0.5;
          float r = length(uv);
          float a = atan(uv.y, uv.x);
          float swirl = noise(vec2(a * 2.0 + uTime * 0.3, r * 4.0 - uTime * 0.6));
          float glow = smoothstep(0.55, 0.0, r) * (0.6 + 0.4 * swirl);
          vec3 col = mix(uColorB, uColorA, glow);
          float alpha = smoothstep(0.6, 0.05, r);
          gl_FragColor = vec4(col, alpha);
        }
      `,
    });
    const portal = new THREE.Mesh(portalGeo, portalMat);
    portal.position.set(0, 0.1, -0.1);
    doorGroup.add(portal);

    // Floating particles / dust
    const particleCount = 220;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const speeds = new Float32Array(particleCount);
    for (let i = 0; i < particleCount; i++) {
      positions[i * 3 + 0] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 6;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 6 - 1;
      speeds[i] = 0.0015 + Math.random() * 0.004;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0xffd29a,
      size: 0.04,
      transparent: true,
      opacity: 0.7,
      depthWrite: false,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // Background subtle starfield
    const starGeo = new THREE.BufferGeometry();
    const starCount = 400;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      starPos[i * 3 + 0] = (Math.random() - 0.5) * 60;
      starPos[i * 3 + 1] = (Math.random() - 0.5) * 30;
      starPos[i * 3 + 2] = -10 - Math.random() * 30;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const stars = new THREE.Points(
      starGeo,
      new THREE.PointsMaterial({ color: 0xb8a8ff, size: 0.05, transparent: true, opacity: 0.6 })
    );
    scene.add(stars);

    // Mouse parallax
    const mouse = { x: 0, y: 0 };
    const onMouseMove = (e) => {
      const rect = mount.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = ((e.clientY - rect.top) / rect.height) * 2 - 1;
    };
    mount.addEventListener('mousemove', onMouseMove);

    // Click → zoom into portal
    const handleClick = () => {
      if (zoomingRef.current) return;
      zoomingRef.current = true;
      setZooming(true);
    };
    mount.addEventListener('click', handleClick);

    // Resize
    const onResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener('resize', onResize);

    // Animation loop
    const clock = new THREE.Clock();
    let zoomT = 0;
    let raf;

    const animate = () => {
      const t = clock.getElapsedTime();
      portalMat.uniforms.uTime.value = t;

      // Particles drift upward
      const pos = particleGeo.attributes.position.array;
      for (let i = 0; i < particleCount; i++) {
        pos[i * 3 + 1] += speeds[i];
        if (pos[i * 3 + 1] > 3) pos[i * 3 + 1] = -3;
      }
      particleGeo.attributes.position.needsUpdate = true;

      // Door breathing
      doorGroup.rotation.y = Math.sin(t * 0.3) * 0.02;
      doorLight.intensity = 2.6 + Math.sin(t * 1.4) * 0.5;

      // Camera idle parallax
      if (!zoomingRef.current) {
        camera.position.x += (mouse.x * 0.5 - camera.position.x) * 0.04;
        camera.position.y += (0.6 + -mouse.y * 0.3 - camera.position.y) * 0.04;
        camera.lookAt(0, 0.4, 0);
      } else {
        // Zoom in: ease camera toward and through the portal
        zoomT += 0.012;
        const k = Math.min(zoomT, 1);
        const ease = k * k * (3 - 2 * k); // smoothstep
        camera.position.x = camera.position.x * (1 - ease * 0.4);
        camera.position.y = 0.6 + (0.2 - 0.6) * ease;
        camera.position.z = 8 + (0.3 - 8) * ease;
        camera.lookAt(0, 0.4, 0);

        portalMat.uniforms.uTime.value = t * (1 + ease * 4);

        if (zoomT >= 1) {
          navigate('/login');
          return; // stop animating
        }
      }

      renderer.render(scene, camera);
      raf = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
      mount.removeEventListener('mousemove', onMouseMove);
      mount.removeEventListener('click', handleClick);
      renderer.dispose();
      portalGeo.dispose();
      portalMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      starGeo.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [navigate]);

  return (
    <div className="door-scene">
      <div ref={mountRef} className="door-canvas" />
      {!zooming && (
        <div className="door-hint">
          <h1 className="door-title">The Wardrobe Awaits</h1>
          <p className="door-sub">Click the door to enter</p>
        </div>
      )}
    </div>
  );
}

export default Door;
