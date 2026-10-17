/**
 * Endless Runner Character Configuration System (DC Protocol Oct 2026)
 * Decouples game physics and collision detection from visual presentation.
 * Supports hot-swapping original characters without modifying runner engine.
 */

window.RUNNER_CHARACTERS = {
  volt_fox: {
    id: 'volt_fox',
    name: 'Volt Fox',
    tagline: 'Agile & Electro-Charged',
    primaryColor: '#f97316',
    accentColor: '#fbbf24',
    width: 38,
    height: 44,
    draw(ctx, x, y, frame, state) {
      ctx.save();
      ctx.translate(x, y);

      const isJumping = state === 'JUMPING';
      const legOffset = isJumping ? 0 : Math.sin(frame * 0.35) * 5;

      // Tail
      ctx.fillStyle = '#ea580c';
      ctx.beginPath();
      ctx.ellipse(-6, 20 + Math.sin(frame * 0.25) * 4, 10, 6, Math.PI / 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#fef08a';
      ctx.beginPath();
      ctx.arc(-11, 24 + Math.sin(frame * 0.25) * 4, 4, 0, Math.PI * 2);
      ctx.fill();

      // Body
      ctx.fillStyle = this.primaryColor;
      ctx.beginPath();
      ctx.roundRect(4, 10, 26, 24, 8);
      ctx.fill();

      // White Chest
      ctx.fillStyle = '#fff7ed';
      ctx.beginPath();
      ctx.ellipse(22, 22, 6, 8, 0, 0, Math.PI * 2);
      ctx.fill();

      // Head
      ctx.fillStyle = this.primaryColor;
      ctx.beginPath();
      ctx.roundRect(16, 2, 20, 16, 6);
      ctx.fill();

      // Snout
      ctx.fillStyle = '#fff7ed';
      ctx.beginPath();
      ctx.moveTo(34, 10);
      ctx.lineTo(40, 13);
      ctx.lineTo(34, 16);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#1e293b';
      ctx.beginPath();
      ctx.arc(39, 13, 2, 0, Math.PI * 2);
      ctx.fill();

      // Eye
      ctx.fillStyle = '#0f172a';
      ctx.beginPath();
      ctx.arc(28, 9, 2.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#38bdf8';
      ctx.beginPath();
      ctx.arc(29, 8.5, 1, 0, Math.PI * 2);
      ctx.fill();

      // Ears
      ctx.fillStyle = '#ea580c';
      ctx.beginPath();
      ctx.moveTo(18, 4);
      ctx.lineTo(21, -6);
      ctx.lineTo(25, 4);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = '#fed7aa';
      ctx.beginPath();
      ctx.moveTo(19, 3);
      ctx.lineTo(21, -3);
      ctx.lineTo(23, 3);
      ctx.closePath();
      ctx.fill();

      // Legs
      ctx.fillStyle = '#9a3412';
      if (isJumping) {
        ctx.fillRect(8, 32, 6, 8);
        ctx.fillRect(20, 30, 6, 6);
      } else {
        ctx.fillRect(8, 32 + legOffset, 5, 10 - legOffset);
        ctx.fillRect(22, 32 - legOffset, 5, 10 + legOffset);
      }

      ctx.restore();
    }
  },

  robo_runner: {
    id: 'robo_runner',
    name: 'Robo Runner',
    tagline: 'Cybernetic Precision',
    primaryColor: '#0ea5e9',
    accentColor: '#38bdf8',
    width: 38,
    height: 44,
    draw(ctx, x, y, frame, state) {
      ctx.save();
      ctx.translate(x, y);

      const isJumping = state === 'JUMPING';
      const legOffset = isJumping ? 0 : Math.sin(frame * 0.35) * 6;

      // Thruster / Back Antenna
      ctx.fillStyle = '#64748b';
      ctx.fillRect(2, 12, 5, 8);
      ctx.fillStyle = '#38bdf8';
      ctx.beginPath();
      ctx.arc(0, 16, 3 + Math.sin(frame * 0.5) * 1.5, 0, Math.PI * 2);
      ctx.fill();

      // Metal Torso
      ctx.fillStyle = '#334155';
      ctx.beginPath();
      ctx.roundRect(6, 12, 24, 22, 6);
      ctx.fill();

      // Power Core Chest
      ctx.fillStyle = '#0284c7';
      ctx.beginPath();
      ctx.arc(18, 22, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#7dd3fc';
      ctx.beginPath();
      ctx.arc(18, 22, 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Head
      ctx.fillStyle = '#475569';
      ctx.beginPath();
      ctx.roundRect(10, 0, 22, 14, 4);
      ctx.fill();

      // Glowing Visor
      ctx.fillStyle = '#06b6d4';
      ctx.fillRect(18, 4, 13, 5);
      ctx.fillStyle = '#ecfeff';
      ctx.fillRect(22, 5, 7, 2);

      // Antenna
      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(14, 0);
      ctx.lineTo(11, -5);
      ctx.stroke();
      ctx.fillStyle = '#06b6d4';
      ctx.beginPath();
      ctx.arc(11, -6, 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Piston Legs
      ctx.fillStyle = '#1e293b';
      if (isJumping) {
        ctx.fillRect(10, 32, 6, 8);
        ctx.fillRect(22, 28, 6, 8);
      } else {
        ctx.fillRect(10, 32 + legOffset, 6, 10 - legOffset);
        ctx.fillRect(22, 32 - legOffset, 6, 10 + legOffset);
      }

      ctx.restore();
    }
  },

  astro_rabbit: {
    id: 'astro_rabbit',
    name: 'Astro Rabbit',
    tagline: 'High-Bounce Cosmic Hero',
    primaryColor: '#a855f7',
    accentColor: '#e879f9',
    width: 38,
    height: 44,
    draw(ctx, x, y, frame, state) {
      ctx.save();
      ctx.translate(x, y);

      const isJumping = state === 'JUMPING';
      const earSwing = isJumping ? -8 : Math.sin(frame * 0.3) * 4;
      const legOffset = isJumping ? 0 : Math.sin(frame * 0.35) * 5;

      // Puffy Tail
      ctx.fillStyle = '#f5d0fe';
      ctx.beginPath();
      ctx.arc(2, 26, 5, 0, Math.PI * 2);
      ctx.fill();

      // Body
      ctx.fillStyle = this.primaryColor;
      ctx.beginPath();
      ctx.roundRect(6, 12, 24, 22, 10);
      ctx.fill();

      // Space Suit Patch
      ctx.fillStyle = '#fae8ff';
      ctx.beginPath();
      ctx.arc(18, 22, 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#c026d3';
      ctx.beginPath();
      ctx.arc(18, 22, 3, 0, Math.PI * 2);
      ctx.fill();

      // Head
      ctx.fillStyle = this.primaryColor;
      ctx.beginPath();
      ctx.roundRect(14, 4, 18, 16, 8);
      ctx.fill();

      // Eye
      ctx.fillStyle = '#0f172a';
      ctx.beginPath();
      ctx.arc(26, 11, 2.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(27, 10, 1, 0, Math.PI * 2);
      ctx.fill();

      // Long Ears with Dynamic Tilt
      ctx.fillStyle = '#9333ea';
      ctx.beginPath();
      ctx.ellipse(16 + earSwing, -4, 4, 12, -0.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#f0abfc';
      ctx.beginPath();
      ctx.ellipse(16 + earSwing, -4, 2, 8, -0.2, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#9333ea';
      ctx.beginPath();
      ctx.ellipse(22 + earSwing * 0.7, -5, 4, 12, 0.1, 0, Math.PI * 2);
      ctx.fill();

      // Legs
      ctx.fillStyle = '#6b21a8';
      if (isJumping) {
        ctx.fillRect(8, 32, 6, 8);
        ctx.fillRect(20, 28, 7, 8);
      } else {
        ctx.fillRect(9, 32 + legOffset, 6, 10 - legOffset);
        ctx.fillRect(21, 32 - legOffset, 6, 10 + legOffset);
      }

      ctx.restore();
    }
  },

  cyber_duck: {
    id: 'cyber_duck',
    name: 'Cyber Duck',
    tagline: 'Quirky Neon Avian',
    primaryColor: '#eab308',
    accentColor: '#14b8a6',
    width: 38,
    height: 44,
    draw(ctx, x, y, frame, state) {
      ctx.save();
      ctx.translate(x, y);

      const isJumping = state === 'JUMPING';
      const wingFlap = isJumping ? Math.sin(frame * 0.6) * 6 : Math.sin(frame * 0.3) * 3;
      const legOffset = isJumping ? 0 : Math.sin(frame * 0.35) * 5;

      // Tail Feathers
      ctx.fillStyle = '#ca8a04';
      ctx.beginPath();
      ctx.moveTo(4, 20);
      ctx.lineTo(-4, 16);
      ctx.lineTo(4, 24);
      ctx.closePath();
      ctx.fill();

      // Body
      ctx.fillStyle = this.primaryColor;
      ctx.beginPath();
      ctx.roundRect(4, 12, 26, 22, 10);
      ctx.fill();

      // Neon Wing
      ctx.fillStyle = '#0d9488';
      ctx.beginPath();
      ctx.ellipse(14, 22 + wingFlap, 9, 6, Math.PI / 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#2dd4bf';
      ctx.beginPath();
      ctx.arc(14, 22 + wingFlap, 3, 0, Math.PI * 2);
      ctx.fill();

      // Head
      ctx.fillStyle = this.primaryColor;
      ctx.beginPath();
      ctx.arc(26, 10, 11, 0, Math.PI * 2);
      ctx.fill();

      // Visor Eye
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(24, 7, 7, 4);
      ctx.fillStyle = '#38bdf8';
      ctx.fillRect(25, 8, 5, 2);

      // Duck Bill
      ctx.fillStyle = '#ea580c';
      ctx.beginPath();
      ctx.roundRect(32, 10, 10, 6, 3);
      ctx.fill();

      // Webbed Legs
      ctx.fillStyle = '#c2410c';
      if (isJumping) {
        ctx.fillRect(10, 32, 5, 8);
        ctx.fillRect(20, 29, 6, 8);
      } else {
        ctx.fillRect(10, 32 + legOffset, 5, 10 - legOffset);
        ctx.fillRect(22, 32 - legOffset, 5, 10 + legOffset);
      }

      ctx.restore();
    }
  }
};
