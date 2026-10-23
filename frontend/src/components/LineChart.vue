<template>
  <div class="frappe-line-chart-container" ref="containerRef">
    <!-- Optional Header -->
    <div v-if="title || subtitle || $slots.header" class="chart-header">
      <slot name="header">
        <div>
          <div v-if="title" class="chart-title">{{ title }}</div>
          <div v-if="subtitle" class="chart-subtitle">{{ subtitle }}</div>
        </div>
      </slot>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="chart-state chart-loading" :style="{ height }">
      <div class="chart-spinner"></div>
      <div class="chart-state-text">正在加载图表数据...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="chart-state chart-error" :style="{ height }">
      <div class="chart-error-icon">⚠️</div>
      <div class="chart-state-text">{{ error }}</div>
    </div>

    <!-- Empty State -->
    <div v-else-if="isEmpty" class="chart-state chart-empty" :style="{ height }">
      <div class="chart-empty-icon">📊</div>
      <div class="chart-state-text">所选周期暂无可用数据</div>
    </div>

    <!-- Active Chart Canvas -->
    <div
      v-show="!loading && !error && !isEmpty"
      ref="chartRef"
      class="frappe-echart-canvas"
      :style="{ height }"
    ></div>

    <!-- Frappe UI Interactive Legend -->
    <div
      v-if="!loading && !error && !isEmpty && resolvedSeries.length > 1"
      class="frappe-chart-legend"
    >
      <button
        v-for="s in resolvedSeries"
        :key="s.name"
        type="button"
        class="legend-item-btn"
        :class="{ 'is-hidden': internalHiddenSeries.includes(s.name) }"
        @click="toggleSeries(s.name)"
        :title="internalHiddenSeries.includes(s.name) ? `点击显示 ${s.label}` : `点击隐藏 ${s.label}`"
      >
        <span
          class="legend-pill"
          :style="{
            backgroundColor: s.color,
            borderStyle: s.dashed ? 'dashed' : 'solid',
            borderWidth: s.dashed ? '2px' : '0px',
            borderColor: s.color,
            background: s.dashed ? 'transparent' : s.color
          }"
        ></span>
        <span class="legend-text">{{ s.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Array,
    default: () => [],
  },
  x: {
    type: String,
    default: 'x',
  },
  y: {
    type: [String, Array],
    default: () => [],
  },
  seriesConfig: {
    type: Object,
    default: () => ({}),
  },
  dashed: {
    type: Boolean,
    default: false,
  },
  smooth: {
    type: Boolean,
    default: true,
  },
  showDataPoints: {
    type: Boolean,
    default: true,
  },
  connectNulls: {
    type: Boolean,
    default: true,
  },
  showDataLabels: {
    type: Boolean,
    default: false,
  },
  hiddenSeries: {
    type: Array,
    default: () => [],
  },
  tooltipColumns: {
    type: Array,
    default: () => [], // [{ name: 'orders', label: 'Orders', format: (val) => ... }]
  },
  referenceLines: {
    type: Array,
    default: () => [], // [{ value: 20, axis: 'y', label: '目标', color: '#94a3b8', dashed: true }]
  },
  xAxis: {
    type: Object,
    default: () => ({}), // { title?: string, type?: string, format?: Function }
  },
  yAxis: {
    type: Object,
    default: () => ({}), // { title?: string, min?: number, max?: number, format?: Function }
  },
  palette: {
    type: [Array, String],
    default: () => [
      '#4f46e5', // indigo
      '#059669', // emerald
      '#ea580c', // orange
      '#db2777', // pink
      '#0284c7', // light blue
      '#7c3aed', // purple
      '#d97706', // amber
      '#0d9488', // teal
      '#64748b', // slate
    ],
  },
  title: {
    type: String,
    default: '',
  },
  subtitle: {
    type: String,
    default: '',
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: null,
  },
  height: {
    type: String,
    default: '320px',
  },
})

const emit = defineEmits(['update:hiddenSeries', 'datapointClick'])

const containerRef = ref(null)
const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null

// Internal tracked hidden series for v-model sync
const internalHiddenSeries = ref([...props.hiddenSeries])

watch(
  () => props.hiddenSeries,
  (newVal) => {
    internalHiddenSeries.value = [...newVal]
    updateChart()
  },
  { deep: true }
)

const toggleSeries = (seriesName) => {
  const index = internalHiddenSeries.value.indexOf(seriesName)
  if (index > -1) {
    internalHiddenSeries.value.splice(index, 1)
  } else {
    internalHiddenSeries.value.push(seriesName)
  }
  emit('update:hiddenSeries', [...internalHiddenSeries.value])
  updateChart()
}

// Normalized y keys
const yKeys = computed(() => {
  if (Array.isArray(props.y)) return props.y
  if (typeof props.y === 'string' && props.y) return [props.y]
  return []
})

// Color palette
const colorPalette = computed(() => {
  if (Array.isArray(props.palette)) return props.palette
  return ['#4f46e5', '#059669', '#ea580c', '#db2777', '#0284c7', '#7c3aed', '#d97706', '#0d9488']
})

// Resolve series descriptors
const resolvedSeries = computed(() => {
  const keys = yKeys.value
  const colors = colorPalette.value

  return keys.map((key, idx) => {
    const custom = props.seriesConfig[key] || {}
    const defaultColor = colors[idx % colors.length]
    return {
      name: key,
      label: custom.label || key,
      color: custom.color || defaultColor,
      type: custom.type || 'line',
      dashed: custom.dashed !== undefined ? custom.dashed : props.dashed,
      smooth: custom.smooth !== undefined ? custom.smooth : props.smooth,
      showDataPoints: custom.showDataPoints !== undefined ? custom.showDataPoints : props.showDataPoints,
      connectNulls: custom.connectNulls !== undefined ? custom.connectNulls : props.connectNulls,
      showDataLabels: custom.showDataLabels !== undefined ? custom.showDataLabels : props.showDataLabels,
      format: custom.format,
    }
  })
})

// Check if data is empty
const isEmpty = computed(() => {
  if (!props.data || props.data.length === 0) return true
  // Check if at least one series has values
  const keys = yKeys.value
  if (!keys.length) return true
  return false
})

const getXValues = () => {
  const xKey = props.x
  return props.data.map((row) => (row[xKey] !== undefined ? row[xKey] : ''))
}

// Build ECharts Option following Frappe UI LineChart specs
const buildChartOption = () => {
  const xCategories = getXValues()
  const seriesDefinitions = resolvedSeries.value

  // Reference lines markLine data
  const markLineData = props.referenceLines.map((refLine) => {
    const isY = !refLine.axis || refLine.axis === 'y'
    const item = isY
      ? { yAxis: refLine.value }
      : { xAxis: refLine.value }

    return {
      ...item,
      label: {
        show: !!refLine.label,
        formatter: refLine.label || '',
        position: 'end',
        color: refLine.color || '#64748b',
        fontSize: 11,
        fontWeight: 600,
      },
      lineStyle: {
        type: refLine.dashed ? 'dashed' : 'solid',
        color: refLine.color || '#94a3b8',
        width: 1.5,
      },
    }
  })

  const seriesList = seriesDefinitions.map((s) => {
    const isHidden = internalHiddenSeries.value.includes(s.name)
    const seriesValues = props.data.map((row) => {
      const val = row[s.name]
      return val === undefined || val === null ? null : val
    })

    const isArea = s.type === 'area'

    const seriesItem = {
      name: s.name,
      type: 'line',
      data: isHidden ? [] : seriesValues,
      smooth: s.smooth,
      connectNulls: s.connectNulls,
      showSymbol: s.showDataPoints,
      symbol: 'circle',
      symbolSize: 6,
      itemStyle: {
        color: s.color,
        borderColor: '#ffffff',
        borderWidth: 2,
      },
      lineStyle: {
        color: s.color,
        width: s.dashed ? 2.5 : 2.2,
        type: s.dashed ? 'dashed' : 'solid',
      },
      label: {
        show: s.showDataLabels,
        position: 'top',
        formatter: (param) => {
          if (s.format) return s.format(param.value)
          return param.value
        },
        fontSize: 10,
        color: '#475569',
      },
    }

    if (isArea) {
      seriesItem.areaStyle = {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: `${s.color}40` },
          { offset: 1, color: `${s.color}05` },
        ]),
      }
    }

    if (markLineData.length && s === seriesDefinitions[0]) {
      seriesItem.markLine = {
        symbol: ['none', 'none'],
        silent: true,
        data: markLineData,
      }
    }

    return seriesItem
  })

  return {
    animation: true,
    animationDuration: 450,
    grid: {
      left: '4%',
      right: '4%',
      top: '12%',
      bottom: '12%',
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: '#cbd5e1',
          width: 1.2,
          type: 'dashed',
        },
      },
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: {
        color: '#1e293b',
        fontSize: 12,
        fontFamily: 'inherit',
      },
      extraCssText: 'box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.05); border-radius: 8px; z-index: 1000;',
      formatter: (params) => {
        if (!params || !params.length) return ''
        const dataIndex = params[0].dataIndex
        const rowData = props.data[dataIndex] || {}
        const displayTitle = rowData.full_label || rowData.label || xLabel
        let html = `<div style="font-weight: 700; margin-bottom: 8px; color: #0f172a; font-size: 13px; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">`
        html += `${displayTitle}`
        html += `</div>`

        html += `<div style="display: flex; flex-direction: column; gap: 6px;">`

        // Series items
        params.forEach((p) => {
          const sMeta = seriesDefinitions.find((m) => m.name === p.seriesName)
          const seriesLabel = sMeta ? sMeta.label : p.seriesName
          const color = sMeta ? sMeta.color : p.color
          const val = p.value !== null && p.value !== undefined ? p.value : '-'
          const formattedVal = sMeta && sMeta.format ? sMeta.format(val) : val

          html += `<div style="display: flex; align-items: center; justify-content: space-between; gap: 18px; min-width: 140px;">`
          html += `<span style="display: flex; align-items: center; gap: 6px; color: #475569; font-size: 12px;">`
          html += `<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${color};"></span>`
          html += `<span>${seriesLabel}</span>`
          html += `</span>`
          html += `<span style="font-weight: 700; color: #0f172a; font-family: monospace; font-size: 12px;">${formattedVal}</span>`
          html += `</div>`
        })

        // Tooltip context columns (if configured via :tooltip-columns)
        if (props.tooltipColumns && props.tooltipColumns.length) {
          html += `<div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed #e2e8f0; display: flex; flex-direction: column; gap: 4px;">`
          props.tooltipColumns.forEach((col) => {
            const raw = rowData[col.name]
            const val = col.format ? col.format(raw) : raw
            const label = col.label || col.name
            html += `<div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; color: #64748b; font-size: 11px;">`
            html += `<span>${label}</span>`
            html += `<span style="font-weight: 600; color: #334155;">${val !== undefined ? val : '-'}</span>`
            html += `</div>`
          })
          html += `</div>`
        }

        html += `</div>`
        return html
      },
    },
    xAxis: {
      type: props.xAxis.type || 'category',
      data: xCategories,
      boundaryGap: false,
      axisLine: {
        lineStyle: {
          color: '#cbd5e1',
          width: 1,
        },
      },
      axisTick: {
        show: true,
        lineStyle: {
          color: '#cbd5e1',
        },
      },
      axisLabel: {
        color: '#64748b',
        fontSize: 11,
        formatter: props.xAxis.format ? props.xAxis.format : undefined,
      },
      name: props.xAxis.title || '',
      nameLocation: 'end',
      nameTextStyle: {
        color: '#94a3b8',
        fontSize: 11,
        padding: [0, 0, 0, 8],
      },
      splitLine: {
        show: false,
      },
    },
    yAxis: {
      type: 'value',
      min: props.yAxis.min,
      max: props.yAxis.max,
      name: props.yAxis.title || '',
      nameTextStyle: {
        color: '#64748b',
        fontSize: 11,
        fontWeight: 600,
        padding: [0, 0, 6, 0],
      },
      axisLabel: {
        color: '#64748b',
        fontSize: 11,
        formatter: (val) => {
          if (props.yAxis.format) return props.yAxis.format(val)
          return val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val
        },
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: '#f1f5f9',
          type: 'dashed',
          width: 1,
        },
      },
    },
    series: seriesList,
  }
}

const updateChart = () => {
  if (!chartInstance || isEmpty.value) return
  const option = buildChartOption()
  chartInstance.setOption(option, true)
}

const initChart = () => {
  if (!chartRef.value) return
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value, null, { renderer: 'canvas' })
  updateChart()

  chartInstance.on('click', (params) => {
    emit('datapointClick', {
      name: params.seriesName,
      value: params.value,
      dataIndex: params.dataIndex,
      row: props.data[params.dataIndex],
    })
  })

  // ResizeObserver for modern fluid responsiveness
  if (containerRef.value && !resizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      if (chartInstance) {
        chartInstance.resize()
      }
    })
    resizeObserver.observe(containerRef.value)
  }
}

watch(
  [() => props.data, () => props.y, () => props.seriesConfig, () => props.referenceLines, () => props.xAxis, () => props.yAxis],
  () => {
    nextTick(() => {
      if (!chartInstance && !isEmpty.value && chartRef.value) {
        initChart()
      } else {
        updateChart()
      }
    })
  },
  { deep: true }
)

onMounted(() => {
  nextTick(() => {
    if (!isEmpty.value) {
      initChart()
    }
  })
})

onBeforeUnmount(() => {
  if (resizeObserver && containerRef.value) {
    resizeObserver.unobserve(containerRef.value)
    resizeObserver.disconnect()
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

defineExpose({
  chart: computed(() => chartInstance),
  resize: () => chartInstance?.resize(),
})
</script>

<style scoped>
.frappe-line-chart-container {
  position: relative;
  width: 100%;
}

.chart-header {
  margin-bottom: 16px;
}

.chart-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary, #0f172a);
}

.chart-subtitle {
  font-size: 0.82rem;
  color: var(--text-muted, #64748b);
  margin-top: 4px;
}

.frappe-echart-canvas {
  width: 100%;
  transition: opacity 0.2s ease;
}

/* Frappe UI Interactive Legend */
.frappe-chart-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle, #f1f5f9);
}

.legend-item-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-size: 0.82rem;
  color: var(--text-secondary, #334155);
  transition: all 0.15s ease;
  user-select: none;
}

.legend-item-btn:hover {
  background: #f8fafc;
  border-color: #e2e8f0;
}

.legend-item-btn.is-hidden {
  opacity: 0.42;
  text-decoration: line-through;
}

.legend-pill {
  width: 14px;
  height: 4px;
  border-radius: 2px;
  display: inline-block;
  flex-shrink: 0;
}

.legend-text {
  font-weight: 500;
}

/* States */
.chart-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px dashed #e2e8f0;
}

.chart-state-text {
  font-size: 0.88rem;
  color: var(--text-muted, #64748b);
}

.chart-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: var(--primary, #2563eb);
  border-radius: 50%;
  animation: chart-spin 0.8s linear infinite;
}

.chart-error-icon,
.chart-empty-icon {
  font-size: 28px;
}

@keyframes chart-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
