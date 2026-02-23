<template>
	<a-card :bordered="false">
		<!-- 页面头部：如果是从客户端列表点进来的，显示返回按钮和当前终端ID -->
		<a-page-header
			v-if="route.query.safeId"
			title="web攻击记录"
			@back="goBack"
			class="pb-0"
		>
			<template #subTitle>
				当前监控终端: <a-tag color="blue">{{ route.query.safeId }}</a-tag>
			</template>
		</a-page-header>

		<!-- 指令下发面板（仅在指定了终端时显示） -->
		<a-card
			v-if="route.query.safeId"
			title="指令下发"
			size="small"
			style="margin: 16px 0"
			:body-style="{ padding: '16px' }"
		>
			<a-row :gutter="16">
				<!-- 自动IP拉黑 -->
				<a-col :span="6">
					<a-card size="small" :bordered="true" style="height: 100%">
						<template #title>
							<span>自动IP拉黑</span>
						</template>
						<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
							<a-switch
								v-model:checked="autoBlockEnabled"
								:loading="autoBlockLoading"
								checked-children="开"
								un-checked-children="关"
							/>
							<span :style="{ color: autoBlockEnabled ? '#52c41a' : '#999' }">
								{{ autoBlockEnabled ? '自动拉黑已开启' : '自动拉黑已关闭' }}
							</span>
						</div>
						<a-button
							type="primary"
							size="small"
							:loading="autoBlockLoading"
							@click="handleAutoBlock"
						>
							下发指令
						</a-button>
					</a-card>
				</a-col>

				<!-- 封禁指定IP -->
				<a-col :span="6">
					<a-card size="small" :bordered="true" style="height: 100%">
						<template #title>
							<span>封禁指定IP</span>
						</template>
						<a-input
							v-model:value="blockIpInput"
							placeholder="请输入要封禁的IP地址"
							allow-clear
							style="margin-bottom: 8px"
						/>
						<a-button
							type="primary"
							danger
							size="small"
							:disabled="!blockIpInput.trim()"
							:loading="blockIpLoading"
							@click="handleBlockIp"
						>
							封禁IP
						</a-button>
					</a-card>
				</a-col>

				<!-- IP白名单 -->
				<a-col :span="6">
					<a-card size="small" :bordered="true" style="height: 100%">
						<template #title>
							<span>更新IP白名单</span>
						</template>
						<a-textarea
							v-model:value="whitelistInput"
							placeholder="每行一个IP或CIDR，如：&#10;192.168.1.1&#10;10.0.0.0/8"
							:rows="3"
							style="margin-bottom: 8px; font-size: 12px"
						/>
						<a-button
							type="primary"
							size="small"
							:loading="whitelistLoading"
							@click="handleWhitelist"
						>
							更新白名单
						</a-button>
					</a-card>
				</a-col>

				<!-- 远程关机 -->
				<a-col :span="6">
					<a-card size="small" :bordered="true" style="height: 100%">
						<template #title>
							<span style="color: #ff4d4f">远程关机</span>
						</template>
						<p style="color: #ff4d4f; font-size: 12px; margin-bottom: 12px;">
							此操作将立即关闭终端系统，请谨慎操作！
						</p>
						<a-popconfirm
							title="确定要发送关机指令吗？"
							description="终端系统将在 5 秒后强制关机，此操作不可撤销。"
							ok-text="确认关机"
							cancel-text="取消"
							ok-type="danger"
							@confirm="handleShutdown"
						>
							<a-button
								type="primary"
								danger
								size="small"
								block
								:loading="shutdownLoading"
							>
								发送关机指令
							</a-button>
						</a-popconfirm>
					</a-card>
				</a-col>
			</a-row>
		</a-card>

		<!-- 搜索表单 -->
		<a-form ref="searchFormRef" name="advanced_search" :model="searchFormState" class="ant-advanced-search-form">
			<a-row :gutter="24">
				<a-col :span="6">
					<a-form-item label="源IP" name="sourceIp">
						<a-input v-model:value="searchFormState.sourceIp" placeholder="请输入攻击源IP" allow-clear />
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-form-item label="威胁等级" name="level">
						<a-select v-model:value="searchFormState.level" placeholder="请选择威胁等级" allow-clear>
							<a-select-option value="高危">高危</a-select-option>
							<a-select-option value="中危">中危</a-select-option>
							<a-select-option value="低危">低危</a-select-option>
						</a-select>
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-form-item label="攻击类型" name="attackType">
						<a-select v-model:value="searchFormState.attackType" placeholder="请选择攻击类型" allow-clear>
							<a-select-option value="port_scan">端口扫描</a-select-option>
							<a-select-option value="sql_injection">SQL 注入</a-select-option>
							<a-select-option value="xss_attempt">XSS 跨站脚本</a-select-option>
							<a-select-option value="dir_traversal">目录遍历</a-select-option>
							<a-select-option value="cmd_injection">命令注入</a-select-option>
							<a-select-option value="csrf_attempt">CSRF 跨站请求伪造</a-select-option>
							<a-select-option value="rce_attempt">远程代码执行</a-select-option>
						</a-select>
					</a-form-item>
				</a-col>
				<a-col :span="6">
					<a-button type="primary" @click="tableRef.refresh(true)">查询</a-button>
					<a-button style="margin-left: 8px" @click="reset">重置</a-button>
				</a-col>
			</a-row>
		</a-form>

		<!-- 数据表格：自带翻页功能 -->
		<s-table
			ref="tableRef"
			:columns="columns"
			:data="loadData"
			:alert="false"
			bordered
			:row-key="(record) => record.id"
		>
			<template #bodyCell="{ column, record }">
				<!-- 攻击类型 中文映射 -->
				<template v-if="column.dataIndex === 'attackType'">
					{{ getAttackTypeName(record.attackType) }}
				</template>

				<!-- 威胁等级 颜色标签 -->
				<template v-if="column.dataIndex === 'level'">
					<a-tag :color="getLevelColor(record.level)">
						{{ record.level }}
					</a-tag>
				</template>

				<!-- 操作列 -->
				<template v-if="column.dataIndex === 'action'">
					<a-space>
						<a @click="openDetail(record)">详情</a>
						<a-divider type="vertical" />
						<a @click="quickBlockIp(record.sourceIp)" style="color: #faad14">封禁IP</a>
						<a-divider type="vertical" />
						<a-popconfirm title="确定要删除这条攻击记录吗？" @confirm="handleDelete(record)">
							<a class="ant-typography ant-typography-danger">删除</a>
						</a-popconfirm>
					</a-space>
				</template>
			</template>
		</s-table>

		<!-- 详情展示弹窗 -->
		<a-modal
			v-model:visible="detailVisible"
			title="Web攻击记录详情"
			width="800px"
			:footer="null"
			@cancel="closeDetail"
		>
			<a-descriptions bordered :column="2" size="small" v-if="detailData">
				<!-- 公共参数区域 -->
				<a-descriptions-item label="记录ID" :span="2">{{ detailData.id }}</a-descriptions-item>
				<a-descriptions-item label="项目ID">{{ detailData.projectId || '-' }}</a-descriptions-item>
				<a-descriptions-item label="终端ID">{{ detailData.safeId || '-' }}</a-descriptions-item>
				<a-descriptions-item label="攻击时间">{{ detailData.attackTime || '-' }}</a-descriptions-item>
				<a-descriptions-item label="源IP">
					{{ detailData.sourceIp || '-' }}
					<a-button
						v-if="detailData.sourceIp && route.query.safeId"
						type="link"
						danger
						size="small"
						style="padding: 0 4px; margin-left: 8px"
						@click="quickBlockIp(detailData.sourceIp)"
					>
						封禁
					</a-button>
				</a-descriptions-item>
				<a-descriptions-item label="攻击类型">{{ getAttackTypeName(detailData.attackType) }}</a-descriptions-item>
				<a-descriptions-item label="威胁等级">
					<a-tag :color="getLevelColor(detailData.level)">{{ detailData.level || '-' }}</a-tag>
				</a-descriptions-item>

				<!-- Web Attack 详细参数区域 -->
				<a-descriptions-item label="请求方法">{{ detailData.requestMethod || '-' }}</a-descriptions-item>
				<a-descriptions-item label="检测方法">{{ detailData.detectionMethod || '-' }}</a-descriptions-item>
				<a-descriptions-item label="请求URI" :span="2">
					<span style="word-break: break-all;">{{ detailData.requestUri || '-' }}</span>
				</a-descriptions-item>
				<a-descriptions-item label="匹配规则 (Pattern)" :span="2">
					<span style="word-break: break-all;">{{ detailData.matchedPattern || '-' }}</span>
				</a-descriptions-item>
				<a-descriptions-item label="User-Agent" :span="2">
					<span style="word-break: break-all;">{{ detailData.userAgent || '-' }}</span>
				</a-descriptions-item>
				<a-descriptions-item label="Referer" :span="2">
					<span style="word-break: break-all;">{{ detailData.referer || '-' }}</span>
				</a-descriptions-item>

				<!-- 端口与扫描等其他参数 -->
				<a-descriptions-item label="协议 (Protocol)">{{ detailData.protocol || '-' }}</a-descriptions-item>
				<a-descriptions-item label="目标端口">{{ detailData.destPort || '-' }}</a-descriptions-item>
				<a-descriptions-item label="扫描类型">{{ getScanTypeName(detailData.scanType) }}</a-descriptions-item>
				<a-descriptions-item label="持续时间">{{ detailData.duration || '-' }}</a-descriptions-item>
				<a-descriptions-item label="目标端口(组)" :span="2">{{ detailData.targetPorts || '-' }}</a-descriptions-item>
				<a-descriptions-item label="Payload 片段" :span="2">
					<div style="background-color: #f5f5f5; padding: 8px; border-radius: 4px; word-break: break-all; max-height: 150px; overflow-y: auto;">
						{{ detailData.payloadSnippet || '无' }}
					</div>
				</a-descriptions-item>
			</a-descriptions>
		</a-modal>
	</a-card>
</template>

<script setup name="webattackIndex">
import {ref, reactive} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {message} from 'ant-design-vue'
import webAttackApi from '@/api/ewm/webattack'
import ewmProjectSafeApi from '@/api/ewm/ewmProjectSafeApi'

const route = useRoute()
const router = useRouter()

const tableRef = ref()
const searchFormRef = ref()
const searchFormState = reactive({
	sourceIp: '',
	level: '',
	attackType: ''
})

// 表头定义 (仅展示公共参数部分)
const columns = [
	{title: '攻击时间', dataIndex: 'attackTime', sorter: true, width: 170},
	{title: '终端ID', dataIndex: 'safeId', width: 120},
	{title: '攻击类型', dataIndex: 'attackType', width: 150},
	{title: '源IP', dataIndex: 'sourceIp', width: 130},
	{title: '威胁等级', dataIndex: 'level', width: 100, align: 'center'},
	{title: '操作', dataIndex: 'action', width: 180, align: 'center', fixed: 'right'}
]

// 详情弹窗状态
const detailVisible = ref(false)
const detailData = ref(null)

// ----------------------------------------------------------------
// 指令下发状态
// ----------------------------------------------------------------
const autoBlockEnabled = ref(false)
const autoBlockLoading = ref(false)

const blockIpInput = ref('')
const blockIpLoading = ref(false)

const whitelistInput = ref('')
const whitelistLoading = ref(false)

const shutdownLoading = ref(false)

// ----------------------------------------------------------------
// 指令下发处理函数
// ----------------------------------------------------------------

const handleAutoBlock = () => {
	autoBlockLoading.value = true
	ewmProjectSafeApi.sendAutoBlock({
		clientId: route.query.safeId,
		enabled: autoBlockEnabled.value
	}).then(() => {
		message.success(`自动拉黑已${autoBlockEnabled.value ? '开启' : '关闭'}`)
	}).catch(() => {
		// 恢复原状态
		autoBlockEnabled.value = !autoBlockEnabled.value
	}).finally(() => {
		autoBlockLoading.value = false
	})
}

const handleBlockIp = () => {
	const ip = blockIpInput.value.trim()
	if (!ip) {
		message.warning('请输入要封禁的IP地址')
		return
	}
	blockIpLoading.value = true
	ewmProjectSafeApi.sendBlockIp({
		clientId: route.query.safeId,
		ip
	}).then(() => {
		message.success(`封禁指令已下发：${ip}`)
		blockIpInput.value = ''
	}).finally(() => {
		blockIpLoading.value = false
	})
}

const handleWhitelist = () => {
	const ips = whitelistInput.value
		.split('\n')
		.map((s) => s.trim())
		.filter((s) => s.length > 0)
	whitelistLoading.value = true
	ewmProjectSafeApi.sendWhitelist({
		clientId: route.query.safeId,
		ips
	}).then(() => {
		message.success(`白名单已更新，共 ${ips.length} 条`)
	}).finally(() => {
		whitelistLoading.value = false
	})
}

const handleShutdown = () => {
	shutdownLoading.value = true
	ewmProjectSafeApi.sendShutdown({
		clientId: route.query.safeId
	}).then(() => {
		message.success('关机指令已下发，终端将在 5 秒后关机')
	}).finally(() => {
		shutdownLoading.value = false
	})
}

// 从攻击记录快速封禁来源IP
const quickBlockIp = (ip) => {
	if (!ip || !route.query.safeId) return
	ewmProjectSafeApi.sendBlockIp({
		clientId: route.query.safeId,
		ip
	}).then(() => {
		message.success(`封禁指令已下发：${ip}`)
	})
}

// ----------------------------------------------------------------
// 表格数据加载
// ----------------------------------------------------------------

const loadData = (parameter) => {
	const requestParameters = Object.assign({}, parameter, searchFormState)
	if (route.query.safeId) {
		requestParameters.safeId = route.query.safeId
	}
	return webAttackApi.webAttackPage(requestParameters).then((data) => {
		return data
	})
}

// 重置查询
const reset = () => {
	searchFormRef.value.resetFields()
	tableRef.value.refresh(true)
}

// 返回上一页
const goBack = () => {
	router.back()
}

// 打开详情弹窗
const openDetail = (record) => {
	detailData.value = record
	detailVisible.value = true
}

// 关闭详情弹窗
const closeDetail = () => {
	detailVisible.value = false
	detailData.value = null
}

// 删除记录
const handleDelete = (record) => {
	const params = [{id: record.id}]
	webAttackApi.webAttackDelete(params).then(() => {
		message.success('删除成功')
		tableRef.value.refresh(false)
	}).catch((err) => {
		console.error(err)
	})
}

// 根据威胁等级返回不同颜色
const getLevelColor = (level) => {
	if (!level) return 'default'
	if (level.includes('高')) return 'red'
	if (level.includes('中')) return 'orange'
	if (level.includes('低')) return 'green'
	return 'blue'
}

// 攻击类型映射字典
const attackTypeMap = {
	'port_scan': '端口扫描',
	'sql_injection': 'SQL 注入',
	'xss_attempt': 'XSS 跨站脚本',
	'dir_traversal': '目录遍历',
	'cmd_injection': '命令注入',
	'csrf_attempt': 'CSRF 跨站请求伪造',
	'rce_attempt': '远程代码执行'
}

const getAttackTypeName = (type) => {
	return attackTypeMap[type] || type || '-'
}

// 扫描类型映射字典
const scanTypeMap = {
	'connect_scan': 'TCP 全连接扫描',
	'syn_scan': 'SYN 半开扫描',
	'fin_scan': 'FIN 扫描',
	'null_scan': 'NULL 扫描',
	'xmas_scan': 'XMAS 扫描',
	'ack_scan': 'ACK 扫描',
	'udp_scan': 'UDP 扫描'
}

const getScanTypeName = (type) => {
	return scanTypeMap[type] || type || '-'
}
</script>

<style scoped>
.truncate {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.ant-typography-danger {
	color: #ff4d4f;
}
</style>
