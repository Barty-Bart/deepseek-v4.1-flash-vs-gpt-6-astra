// DOM HUD: resources, selection panel, command card, minimap and overlays.
import {
  COSTS,
  TRAIN_TIME,
  BUILD_TIME,
  BUILDING_STATS,
  UNIT_STATS,
  TEAM,
  AGES,
  MAX_AGE,
  FORMATIONS,
} from './config.js';
import { ICONS } from './icons.js';

const icon = (name) => ICONS.RES[name] || ICONS.BUILD[name] || ICONS.UNIT[name] || ICONS.MISC[name] || ICONS.FORMS[name] || '';

function costHtml(cost) {
  return Object.entries(cost)
    .map(([k, v]) => `<span class="cost"><i class="ci">${icon(k)}</i>${v}</span>`)
    .join('');
}

export class Hud {
  constructor({ game, controls, sound }) {
    this.game = game;
    this.controls = controls;
    this.sound = sound;
    this.els = {
      food: document.getElementById('res-food'),
      wood: document.getElementById('res-wood'),
      gold: document.getElementById('res-gold'),
      pop: document.getElementById('res-pop'),
      ageChip: document.getElementById('age-chip'),
      selTitle: document.getElementById('sel-title'),
      selSub: document.getElementById('sel-sub'),
      selHp: document.getElementById('sel-hp'),
      selHpFill: document.getElementById('sel-hp-fill'),
      selQueue: document.getElementById('sel-queue'),
      selQueueLabel: document.getElementById('sel-queue-label'),
      selQueueFill: document.getElementById('sel-queue-fill'),
      actions: document.getElementById('actions'),
      toasts: document.getElementById('toasts'),
      topbar: document.getElementById('topbar'),
      bottombar: document.getElementById('bottombar'),
      btnHome: document.getElementById('btn-home'),
      btnPause: document.getElementById('btn-pause'),
      btnMute: document.getElementById('btn-mute'),
      btnRestart: document.getElementById('btn-restart'),
      btnHelp: document.getElementById('btn-help'),
      overlayHelp: document.getElementById('overlay-help'),
      overlayPause: document.getElementById('overlay-pause'),
      overlayEnd: document.getElementById('overlay-end'),
      endTitle: document.getElementById('end-title'),
      endBody: document.getElementById('end-body'),
      btnEndRestart: document.getElementById('btn-end-restart'),
      minimap: document.getElementById('minimap'),
      menu: document.getElementById('overlay-menu'),
      btnStart: document.getElementById('btn-start'),
    };
    this.actionSignature = '';
    this.endShown = false;
    this.bind();
    this.refresh(true);
  }

  topHeight() {
    return this.els.topbar.offsetHeight;
  }

  bottomHeight() {
    return this.els.bottombar.offsetHeight;
  }

  bind() {
    const { els } = this;
    // Fill the resource-strip icons from the shared SVG set.
    document.querySelectorAll('.ico[data-icon]').forEach((el) => {
      el.innerHTML = icon(el.dataset.icon);
    });
    els.btnHome.addEventListener('click', () => this.controls.centerOnHome());
    els.btnPause.addEventListener('click', () => this.controls.togglePause());
    els.btnMute.addEventListener('click', () => this.controls.toggleMute());
    els.btnHelp.addEventListener('click', () => this.toggleHelp());
    els.btnRestart.addEventListener('click', () => this.requestRestart());
    els.btnEndRestart.addEventListener('click', () => this.requestRestart());
    els.btnStart.addEventListener('click', () => {
      this.hideMenu();
      if (this.onStartGame) this.onStartGame();
    });
    document.querySelectorAll('[data-close]').forEach((b) =>
      b.addEventListener('click', () => document.getElementById(b.dataset.close).classList.add('hidden')),
    );
    els.minimap.addEventListener('mousedown', (e) => {
      const r = els.minimap.getBoundingClientRect();
      const sx = (e.clientX - r.left) / r.width;
      const sy = (e.clientY - r.top) / r.height;
      this.controls.jumpTo(sx * 80 * 32, sy * 60 * 32);
    });
  }

  setGame(game) {
    this.game = game;
    this.endShown = false;
    this.els.overlayEnd.classList.add('hidden');
    this.els.overlayPause.classList.add('hidden');
    this.actionSignature = '';
    this.refresh(true);
  }

  toast(text, kind = '') {
    const el = document.createElement('div');
    el.className = `toast ${kind}`.trim();
    el.textContent = text;
    this.els.toasts.appendChild(el);
    setTimeout(() => el.remove(), 2800);
  }

  showMenu() {
    this.els.menu.classList.remove('hidden');
  }

  hideMenu() {
    this.els.menu.classList.add('hidden');
  }

  toggleHelp() {
    this.els.overlayHelp.classList.toggle('hidden');
  }

  closeOverlays() {
    this.els.overlayHelp.classList.add('hidden');
  }

  onSelectionChanged() {
    this.actionSignature = '';
    this.refresh(true);
  }

  onPlacingChanged() {
    this.actionSignature = '';
    this.refresh(true);
  }

  onPauseChanged() {
    this.els.overlayPause.classList.toggle('hidden', !this.controls.paused);
    this.els.btnPause.textContent = this.controls.paused ? 'Resume' : 'Pause';
  }

  onMuteChanged() {
    this.els.btnMute.textContent = this.controls.muted ? 'Muted' : 'Sound';
    this.els.btnMute.classList.toggle('off', this.controls.muted);
  }

  requestRestart() {
    this.restartRequested = true;
  }

  // ------------------------------------------------------------- command card

  buildButton(type) {
    const game = this.game;
    const cost = COSTS[type];
    const unlocked = game.buildingUnlocked(TEAM.PLAYER, type);
    const afford = game.canAfford(TEAM.PLAYER, cost);
    const note = {
      house: '+5 population',
      farm: 'renewable food',
      barracks: 'trains soldiers',
      watchtower: 'defends the base',
    }[type];
    return {
      icon: type,
      name: `Build ${BUILDING_STATS[type].name}`,
      cost,
      note: unlocked ? note : `Requires the ${AGES[BUILDING_STATS[type].age || 0].name}`,
      locked: !unlocked,
      disabled: !unlocked || !afford,
      onClick: () => this.controls.startPlacing(type),
    };
  }

  trainButton(building, type) {
    const game = this.game;
    const cost = COSTS[type];
    const unlocked = game.unitUnlocked(building.team, type);
    const afford = game.canAfford(building.team, cost);
    const headroom = building.team === TEAM.PLAYER ? game.popHeadroom(building.team) > 0 : true;
    return {
      icon: type,
      name: `Train ${UNIT_STATS[type].name}`,
      cost,
      note: unlocked
        ? `${TRAIN_TIME[type]}s · ${UNIT_STATS[type].role}`
        : `Requires the ${AGES[UNIT_STATS[type].age || 0].name}`,
      locked: !unlocked,
      disabled: !unlocked || !afford || !headroom || building.queue.length >= 5,
      onClick: () => this.train(building, type),
    };
  }

  formationButtons(units) {
    return FORMATIONS.map((f) => ({
      icon: f.id,
      name: f.name,
      note: this.controls.formation === f.id ? 'current formation' : 're-form the group',
      highlight: this.controls.formation === f.id,
      disabled: units.length < 2,
      onClick: () => {
        this.controls.formation = f.id;
        this.game.reformUnits(units, f.id);
        this.sound.play('command');
        this.actionSignature = '';
        this.refresh(true);
      },
    }));
  }

  stopButton(units) {
    return {
      icon: 'stop',
      name: 'Stop',
      note: 'hold position (X)',
      onClick: () => {
        this.game.commandStop(units);
        this.sound.play('command');
      },
    };
  }

  ageButton(building) {
    const game = this.game;
    const p = game.players[building.team];
    if (building.research) {
      const target = AGES[building.research.to];
      return {
        icon: 'research',
        name: `Advancing to ${target.name}`,
        cost: null,
        note: `${Math.ceil(target.time - building.research.elapsed)}s remaining`,
        disabled: true,
        onClick: null,
      };
    }
    if (p.age >= MAX_AGE) {
      return {
        icon: 'age',
        name: `${AGES[p.age].name} reached`,
        note: 'no further ages',
        disabled: true,
      };
    }
    const next = AGES[p.age + 1];
    const afford = game.canAfford(building.team, next.cost);
    return {
      icon: 'age',
      name: `Advance to ${next.name}`,
      cost: next.cost,
      note: `${next.time}s · ${next.blurb}`,
      disabled: !afford,
      onClick: () => this.research(building),
    };
  }

  actionsForState() {
    const game = this.game;
    const units = this.controls.selectedUnits();
    const building = this.controls.selBuilding;
    const list = [];

    if (this.controls.placing) {
      const s = BUILDING_STATS[this.controls.placing.type];
      list.push({ icon: this.controls.placing.type, name: `Placing ${s.name}`, note: 'left-click to confirm · Esc to cancel' });
      list.push({ icon: 'cancel', name: 'Cancel', note: 'stop placing', onClick: () => this.controls.cancelPlacing() });
      return list;
    }

    if (building && building.team === TEAM.PLAYER) {
      if (!building.complete) {
        list.push({
          icon: building.type,
          name: 'Under construction',
          note: 'right-click with villagers to help build',
          disabled: true,
        });
        return list;
      }
      const trains = BUILDING_STATS[building.type].trains || [];
      for (const type of trains) list.push(this.trainButton(building, type));
      if (BUILDING_STATS[building.type].research) list.push(this.ageButton(building));
      if (building.research) {
        list.push({
          icon: 'cancel',
          name: 'Cancel advance',
          note: 'refunds the cost',
          onClick: () => {
            if (game.cancelResearch(building)) {
              this.sound.play('command');
              this.refresh(true);
            }
          },
        });
      }
      if (building.queue.length) {
        list.push({
          icon: 'cancel',
          name: `Cancel ${UNIT_STATS[building.queue[building.queue.length - 1].type].name}`,
          note: 'refunds the cost',
          onClick: () => {
            if (game.cancelTrain(building)) {
              this.sound.play('command');
              this.refresh(true);
            }
          },
        });
      }
      list.push({
        icon: 'camera',
        name: 'Centre camera',
        note: 'jump to this building',
        onClick: () => this.controls.centerOn(building.x, building.y),
      });
      return list;
    }

    if (building) {
      list.push({
        icon: building.type,
        name: `${BUILDING_STATS[building.type].name} (Ashfell)`,
        note: `enemy structure · ${Math.max(0, Math.ceil(building.hp))} HP`,
        disabled: true,
      });
      return list;
    }

    if (units.length) {
      list.push(this.stopButton(units));
      const villagers = units.filter((u) => u.type === 'villager');
      if (villagers.length) {
        for (const type of ['house', 'farm', 'barracks', 'watchtower']) list.push(this.buildButton(type));
      }
      if (units.length >= 2) for (const b of this.formationButtons(units)) list.push(b);
      return list;
    }

    return list;
  }

  train(building, type) {
    const result = this.game.queueTrain(building, type);
    if (result.ok) this.sound.play('command');
    else {
      this.toast(result.reason, 'warn');
      this.sound.play('error');
    }
    this.refresh(true);
  }

  research(building) {
    const result = this.game.queueResearch(building);
    if (result.ok) {
      this.sound.play('research-start');
      this.toast(`Advancing to the ${result.age.name}…`, 'good');
    } else {
      this.toast(result.reason, 'warn');
      this.sound.play('error');
    }
    this.refresh(true);
  }

  renderActions() {
    const list = this.actionsForState();
    const sig = JSON.stringify(list.map((a) => [a.icon, a.name, a.note, !!a.disabled, !!a.highlight, a.cost || null]));
    if (sig === this.actionSignature && this.els.actions.children.length === list.length) {
      list.forEach((a, i) => this.els.actions.children[i].classList.toggle('disabled', !!a.disabled));
      return;
    }
    this.actionSignature = sig;
    const wrap = this.els.actions;
    wrap.textContent = '';
    for (const a of list) {
      const btn = document.createElement('button');
      btn.className = `action${a.disabled ? ' disabled' : ''}${a.highlight ? ' highlight' : ''}${a.locked ? ' locked' : ''}`;
      btn.innerHTML =
        `<span class="a-icon">${icon(a.icon)}</span>` +
        `<span class="a-text"><span class="a-name">${a.name}</span>` +
        `<span class="a-cost">${a.cost ? `${costHtml(a.cost)} · ` : ''}${a.note || ''}</span></span>`;
      if (!a.disabled && a.onClick) btn.addEventListener('click', a.onClick);
      wrap.appendChild(btn);
    }
  }

  // ------------------------------------------------------------------ refresh

  refresh(force) {
    const game = this.game;
    if (!game) return;
    const p = game.players[TEAM.PLAYER];
    this.els.food.textContent = Math.floor(p.res.food);
    this.els.wood.textContent = Math.floor(p.res.wood);
    this.els.gold.textContent = Math.floor(p.res.gold);
    this.els.pop.textContent = `${p.pop}/${p.maxPop}`;
    this.els.ageChip.textContent = AGES[p.age].name;
    this.els.ageChip.title = AGES[p.age].blurb || '';

    const units = this.controls.selectedUnits();
    const building = this.controls.selBuilding;
    const total = units.length + (building ? 1 : 0);

    let title = 'No selection';
    let sub = 'Drag to select villagers or soldiers. Right-click to command.';
    if (total === 1) {
      if (building) {
        const s = BUILDING_STATS[building.type];
        title = `${s.name}${building.complete ? '' : ' (building)'}`;
        if (!building.complete) {
          sub = `Construction ${Math.floor((building.progress / building.buildTime) * 100)}% · right-click with a villager to help`;
        } else if (building.research) {
          sub = `Advancing to the ${AGES[building.research.to].name}`;
        } else if (building.type === 'farm') {
          sub = `Yours · ${Math.ceil(building.hp)} / ${building.maxHp} HP · villagers gather food here`;
        } else {
          sub = `${building.team === TEAM.PLAYER ? 'Yours' : 'Ashfell'} · ${Math.ceil(building.hp)} / ${building.maxHp} HP`;
        }
      } else {
        const u = units[0];
        const st = UNIT_STATS[u.type];
        title = `${st.name}${u.team === TEAM.PLAYER ? '' : ' (Ashfell)'}`;
        const task = {
          gather: 'gathering', return: 'hauling resources', build: 'building',
          attack: 'fighting', move: 'moving', idle: 'idle',
        }[u.task] || u.task;
        sub = `${st.role} · ${task}`;
        if (u.carry > 0) sub += ` · carrying ${Math.floor(u.carry)}`;
      }
    } else if (total > 1) {
      const groups = {};
      for (const u of units) groups[UNIT_STATS[u.type].name] = (groups[UNIT_STATS[u.type].name] || 0) + 1;
      title = `${total} units selected`;
      sub = Object.entries(groups).map(([k, v]) => `${v} ${k}${v === 1 ? '' : 's'}`).join(' · ');
      sub += ` · ${FORMATIONS.find((f) => f.id === this.controls.formation).name} formation`;
    }
    if (this.els.selTitle.textContent !== title) this.els.selTitle.textContent = title;
    if (this.els.selSub.innerHTML !== sub) this.els.selSub.innerHTML = sub;

    const unitOne = units[0];
    if (total === 1 && (building || unitOne)) {
      this.els.selHp.classList.remove('hidden');
      const frac = building ? building.hp / building.maxHp : unitOne.hp / unitOne.maxHp;
      this.els.selHpFill.style.width = `${Math.max(0, frac * 100)}%`;
    } else {
      this.els.selHp.classList.add('hidden');
    }

    const training = building && building.queue.length ? { item: building.queue[0], label: `Training ${UNIT_STATS[building.queue[0].type].name}` } : null;
    const researching = building && building.research
      ? { item: { elapsed: building.research.elapsed, time: building.research.time }, label: `Researching the ${AGES[building.research.to].name}` }
      : null;
    const job = training || researching;
    if (job) {
      this.els.selQueue.classList.remove('hidden');
      this.els.selQueueLabel.textContent = building.queue.length > 1 && training
        ? `${job.label} (${building.queue.length} queued)`
        : job.label;
      this.els.selQueueFill.style.width = `${Math.min(100, (job.item.elapsed / job.item.time) * 100)}%`;
    } else {
      this.els.selQueue.classList.add('hidden');
    }

    this.renderActions();

    if (game.state !== 'playing' && !this.endShown) {
      this.endShown = true;
      const won = game.state === 'won';
      this.els.endTitle.textContent = won ? 'Victory' : 'Defeat';
      const mm = Math.floor(game.time / 60);
      const ss = Math.floor(game.time % 60);
      const st = game.stats;
      this.els.endBody.innerHTML = won
        ? `Ashfell's town centre is rubble. You settled the vale in <b>${mm}m ${String(ss).padStart(2, '0')}s</b>.<br>
           Gathered ${Math.round(st.gathered.food)} food, ${Math.round(st.gathered.wood)} wood, ${Math.round(st.gathered.gold)} gold · 
           ${st.trained} units trained · ${st.built} buildings raised · ${st.kills} enemies slain · ${st.losses} lost.`
        : `Your town centre has fallen after <b>${mm}m ${String(ss).padStart(2, '0')}s</b>.<br>
           Gathered ${Math.round(st.gathered.food)} food, ${Math.round(st.gathered.wood)} wood, ${Math.round(st.gathered.gold)} gold · 
           ${st.trained} units trained · ${st.built} buildings raised · ${st.kills} enemies slain.`;
      this.els.overlayEnd.classList.remove('hidden');
    }

    void force;
  }
}
