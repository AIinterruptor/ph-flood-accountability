/* global initMap */

const DATA_BASE = 'data';

async function fetchJSON(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to fetch ${url}: ${resp.status}`);
  return resp.json();
}

async function fetchAll(ids, dir) {
  const results = await Promise.allSettled(
    ids.map(id => fetchJSON(`${DATA_BASE}/${dir}/${id}.json`))
  );
  return results
    .filter(r => r.status === 'fulfilled')
    .map(r => r.value);
}

function app() {
  return {
    index: {},
    projects: [],
    persons: [],
    cases: [],
    timeline: [],
    activeTab: 'Projects',
    mapInitialized: false,
    detail: { open: false, type: null, entity: null },
    filter: { region: '', agency: '', status: '', search: '' },

    async init() {
      try {
        this.index = await fetchJSON(`${DATA_BASE}/index.json`);
      } catch (e) {
        console.warn('Could not load index.json — no data yet.', e);
        this.index = { totals: {}, source_health: {}, data_quality: {} };
        return;
      }

      const [projectFiles, personFiles, caseFiles] = await Promise.all([
        this._listDir('projects'),
        this._listDir('persons'),
        this._listDir('cases'),
      ]);

      const [projects, persons, cases, timeline] = await Promise.all([
        fetchAll(projectFiles, 'projects'),
        fetchAll(personFiles, 'persons'),
        fetchAll(caseFiles, 'cases'),
        fetchJSON(`${DATA_BASE}/timeline.json`).catch(() => []),
      ]);

      this.projects = projects;
      this.persons = persons;
      this.cases = cases;
      this.timeline = timeline;
    },

    async _listDir(dir) {
      // We derive the list from _manifest.json written by the scraper.
      // Fall back to empty array if manifest is missing (no data yet).
      try {
        const manifest = await fetchJSON(`${DATA_BASE}/${dir}/_manifest.json`);
        return manifest.ids || [];
      } catch {
        return [];
      }
    },

    switchTab(tab) {
      this.activeTab = tab;
      if (tab === 'Map' && !this.mapInitialized) {
        this.$nextTick(() => {
          initMap(this.projects);
          this.mapInitialized = true;
        });
      }
    },

    filteredProjects() {
      const { region, agency, status, search } = this.filter;
      return this.projects.filter(p => {
        if (region && p.region !== region) return false;
        if (agency && p.agency !== agency) return false;
        if (status && p.status !== status) return false;
        if (search) {
          const q = search.toLowerCase();
          if (!p.name.toLowerCase().includes(q) && !p.agency.toLowerCase().includes(q)) return false;
        }
        return true;
      });
    },

    filteredPersons() {
      const { agency, status, search } = this.filter;
      return this.persons.filter(p => {
        if (agency && p.agency !== agency) return false;
        if (status && p.status !== status) return false;
        if (search) {
          const q = search.toLowerCase();
          if (!p.name.toLowerCase().includes(q) && !p.position.toLowerCase().includes(q)) return false;
        }
        return true;
      });
    },

    filteredCases() {
      const { search } = this.filter;
      return this.cases.filter(c => {
        if (search) {
          const q = search.toLowerCase();
          if (!c.docket.toLowerCase().includes(q) && !c.charge.toLowerCase().includes(q)) return false;
        }
        return true;
      });
    },

    showDetail(type, entity) {
      this.detail = { open: true, type, entity };
    },

    renderDetail() {
      const { type, entity } = this.detail;
      if (!entity) return '';
      const esc = s => String(s).replace(/</g, '&lt;').replace(/>/g, '&gt;');
      const pill = status => `<span class="status-pill status-${esc(status)}">${esc(status.replace('_', ' '))}</span>`;
      const sourceList = sources => (sources || []).map(s =>
        `<li><a href="${esc(s.url)}" target="_blank" class="text-blue-600 underline text-xs">${esc(s.type)} (${esc(s.date)})</a></li>`
      ).join('');

      if (type === 'project') {
        return `
          <h2 class="text-lg font-bold mb-1">${esc(entity.name)}</h2>
          <div class="mb-3">${pill(entity.status)}</div>
          <dl class="text-sm space-y-1 text-gray-700">
            <div><dt class="font-medium inline">Agency:</dt> <dd class="inline">${esc(entity.agency)}</dd></div>
            <div><dt class="font-medium inline">Region:</dt> <dd class="inline">${esc(entity.region)}</dd></div>
            <div><dt class="font-medium inline">Budget:</dt> <dd class="inline">₱${Number(entity.budget_php).toLocaleString()}</dd></div>
            <div><dt class="font-medium inline">COA Findings:</dt> <dd class="inline">${esc(entity.coa_findings.join(', ') || 'None')}</dd></div>
            <div><dt class="font-medium inline">Cases:</dt> <dd class="inline">${esc(entity.cases.join(', ') || 'None')}</dd></div>
          </dl>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Sources</h3>
          <ul class="space-y-1">${sourceList(entity.sources)}</ul>
        `;
      }

      if (type === 'person') {
        return `
          <h2 class="text-lg font-bold mb-1">${esc(entity.name)}</h2>
          <div class="mb-3">${pill(entity.status)}</div>
          <dl class="text-sm space-y-1 text-gray-700">
            <div><dt class="font-medium inline">Position:</dt> <dd class="inline">${esc(entity.position)}</dd></div>
            <div><dt class="font-medium inline">Agency:</dt> <dd class="inline">${esc(entity.agency)}</dd></div>
            <div><dt class="font-medium inline">Admin Track:</dt> <dd class="inline">${esc(entity.admin_track?.stage)} / ${esc(entity.admin_track?.status)}</dd></div>
            <div><dt class="font-medium inline">Criminal Track:</dt> <dd class="inline">${esc(entity.criminal_track?.stage)} / ${esc(entity.criminal_track?.status)}</dd></div>
            <div><dt class="font-medium inline">Cases:</dt> <dd class="inline">${esc((entity.criminal_track?.case_ids || []).join(', ') || 'None')}</dd></div>
          </dl>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Sources</h3>
          <ul class="space-y-1">${sourceList(entity.sources)}</ul>
        `;
      }

      if (type === 'case') {
        const tlItems = (entity.timeline || []).map(ev =>
          `<li class="flex gap-2 text-xs"><span class="text-gray-400 w-24 shrink-0">${esc(ev.date)}</span><span>${esc(ev.event)}</span></li>`
        ).join('');
        return `
          <h2 class="text-lg font-bold mb-1">${esc(entity.docket)}</h2>
          ${entity.discrepancy ? '<div class="text-yellow-600 text-sm mb-2">⚠ Sources conflict on case stage</div>' : ''}
          <dl class="text-sm space-y-1 text-gray-700">
            <div><dt class="font-medium inline">Court:</dt> <dd class="inline">${esc(entity.court)}</dd></div>
            <div><dt class="font-medium inline">Track:</dt> <dd class="inline">${esc(entity.track)}</dd></div>
            <div><dt class="font-medium inline">Charge:</dt> <dd class="inline">${esc(entity.charge)}</dd></div>
            <div><dt class="font-medium inline">Amount:</dt> <dd class="inline">₱${Number(entity.amount_php).toLocaleString()}</dd></div>
            <div><dt class="font-medium inline">Stage:</dt> <dd class="inline">${esc(entity.stage)}</dd></div>
            <div><dt class="font-medium inline">Filed:</dt> <dd class="inline">${esc(entity.filed_date)}</dd></div>
            <div><dt class="font-medium inline">Decision:</dt> <dd class="inline">${esc(entity.decision ?? 'Pending')}</dd></div>
          </dl>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Timeline</h3>
          <ul class="space-y-1">${tlItems || '<li class="text-xs text-gray-400">No timeline events.</li>'}</ul>
          <h3 class="font-semibold mt-4 mb-1 text-sm">Sources</h3>
          <ul class="space-y-1">${sourceList(entity.sources)}</ul>
        `;
      }

      return '';
    },

    formatPHP(n) {
      if (!n) return '0';
      if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'B';
      if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
      if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K';
      return n.toString();
    },
  };
}

window.app = app;
