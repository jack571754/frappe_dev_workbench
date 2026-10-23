<template><svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-for="(d, i) in paths[name] || paths.code" :key="i" :d="d" /></svg></template>
<script setup>
defineProps({ name: String, size: { type: Number, default: 19 } })
const paths = {
  activity: ['M4 19V9m5 10V5m5 14v-7m5 7V3'],
  trend: ['M3 17l6-6 4 4 8-10', 'M15 5h6v6'],
  calendar: ['M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z', 'M8 14h2m4 0h2m-8 3h2'],
  archive: ['M3 3h18v5H3zM5 8v13h14V8m-10 4h6'],
  code: ['m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18'],
  folder: ['M3 7V4h6l3 3h9v13H3Z'],
  members: ['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m18 0v-2a4 4 0 0 0-3-3.87', 'M9 3a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm7 0a4 4 0 0 1 0 8'],
  repository: ['M4 3h16v18H4zM8 3v18m4-13h4m-4 4h4'],
  shield: ['M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7Z', 'm8 12 3 3 5-6'],
  branch: ['M6 3v12m0 0a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm12-12a3 3 0 1 0 0 6 3 3 0 0 0 0-6ZM6 15c0-6 12-1 12-6'],
  refresh: ['M20 7a9 9 0 1 0 1 8M20 2v5h-5'],
  search: ['M11 3a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm6 14 4 4'],
  arrow: ['M5 12h14m-5-5 5 5-5 5'],
  menu: ['M4 6h16M4 12h16M4 18h16'],
  close: ['m6 6 12 12M6 18 18 6'],
}
</script>
