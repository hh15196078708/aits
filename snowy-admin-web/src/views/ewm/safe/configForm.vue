<template>
	<xn-form-container
		title="终端安全配置"
		:width="780"
		:visible="visible"
		:destroy-on-close="true"
		@close="onClose"
	>
		<!-- 步骤条 -->
		<a-steps :current="currentStep" size="small" style="margin-bottom: 24px">
			<a-step title="服务端通信" />
			<a-step title="安全防护" />
			<a-step title="流量与日志监控" />
			<a-step title="资源限制" />
			<a-step title="系统参数" />
		</a-steps>

		<div class="step-content">
			<a-form ref="formRef" :model="formData" layout="vertical">
				<!-- ================================================================ -->
				<!-- 步骤1：服务端通信配置                                             -->
				<!-- ================================================================ -->
				<div v-show="currentStep === 0">
					<!-- 服务端地址 -->
					<a-card title="服务端地址" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="16">
								<a-form-item label="API 基础地址">
									<a-input v-model:value="formData.server.url" placeholder="http://127.0.0.1:82/safe" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="项目ID">
									<a-input v-model:value="formData.server.project_id" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<!-- API端点 -->
					<a-card title="API 端点路径" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="注册接口">
									<a-input v-model:value="formData.server.endpoints.register" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="心跳接口">
									<a-input v-model:value="formData.server.endpoints.heartbeat" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="Web攻击上报">
									<a-input v-model:value="formData.server.endpoints.attack_web" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="端口扫描上报">
									<a-input v-model:value="formData.server.endpoints.attack_portscan" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="流量攻击上报">
									<a-input v-model:value="formData.server.endpoints.attack_traffic" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="攻击阈值获取">
									<a-input v-model:value="formData.server.endpoints.attack_threshold" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="检测器状态上报">
									<a-input v-model:value="formData.server.endpoints.detector_status" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="规则库版本查询">
									<a-input v-model:value="formData.server.endpoints.rule_lib_version" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="规则库更新下载">
									<a-input v-model:value="formData.server.endpoints.rule_lib_update" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<!-- WebSocket -->
					<a-card title="WebSocket 长连接" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="16">
								<a-form-item label="WSS 地址">
									<a-input v-model:value="formData.websocket.url" placeholder="ws://127.0.0.1:82/safe/init/ws" />
									<div class="form-item-tip">连接时自动拼接 /{clientId}</div>
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="重连间隔（秒）">
									<a-input-number v-model:value="formData.websocket.reconnect_interval" :min="1" :max="300" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="SSL 证书验证">
									<a-switch v-model:checked="formData.websocket.ssl_verify" checked-children="开启" un-checked-children="关闭" />
									<div class="form-item-tip">自签名证书可关闭</div>
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<!-- 心跳 -->
					<a-card title="心跳机制" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="6">
								<a-form-item label="心跳间隔（秒）">
									<a-input-number v-model:value="formData.heartbeat.interval" :min="1" :max="300" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="请求超时（秒）">
									<a-input-number v-model:value="formData.heartbeat.request_timeout" :min="1" :max="60" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="最大重试次数">
									<a-input-number v-model:value="formData.heartbeat.max_retry" :min="0" :max="20" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="重试间隔（秒）">
									<a-input-number v-model:value="formData.heartbeat.retry_interval" :min="1" :max="60" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>
				</div>

				<!-- ================================================================ -->
				<!-- 步骤2：安全防护配置                                               -->
				<!-- ================================================================ -->
				<div v-show="currentStep === 1">
					<!-- IP拉黑策略 -->
					<a-card title="IP 自动拉黑" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="启用自动拉黑">
									<a-switch v-model:checked="formData.ip_blocker.enabled" checked-children="开启" un-checked-children="关闭" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="最低攻击级别">
									<a-select v-model:value="formData.ip_blocker.min_attack_level">
										<a-select-option value="low">低危 (low)</a-select-option>
										<a-select-option value="medium">中危 (medium)</a-select-option>
										<a-select-option value="high">高危 (high)</a-select-option>
									</a-select>
									<div class="form-item-tip">仅封禁该级别及以上的攻击IP</div>
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="封禁出站连接">
									<a-switch v-model:checked="formData.ip_blocker.block_outbound" checked-children="是" un-checked-children="否" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="白名单同步间隔（秒）">
									<a-input-number v-model:value="formData.ip_blocker.whitelist_sync_interval" :min="10" :max="86400" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="防火墙规则前缀">
									<a-input v-model:value="formData.ip_blocker.rule_name_prefix" />
								</a-form-item>
							</a-col>
						</a-row>
						<a-form-item label="IP 白名单">
							<a-select
								v-model:value="formData.ipWhitelist"
								mode="tags"
								placeholder="输入IP地址后按回车添加，如 192.168.1.1 或 10.0.0.0/8"
								:token-separators="[',', ' ']"
								allow-clear
							/>
						</a-form-item>
					</a-card>

					<!-- 攻击检测 -->
					<a-card title="攻击检测" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="6">
								<a-form-item label="日志批量大小">
									<a-input-number v-model:value="formData.attack_detection.attack_log_batch_size" :min="1" :max="500" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="上报间隔（秒）">
									<a-input-number v-model:value="formData.attack_detection.attack_log_upload_interval" :min="1" :max="3600" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="检测器最大重启">
									<a-input-number v-model:value="formData.attack_detection.attack_detector_max_restart" :min="0" :max="100" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="重启延迟（秒）">
									<a-input-number v-model:value="formData.attack_detection.attack_detector_restart_delay" :min="1" :max="60" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="规则库文件路径">
									<a-input v-model:value="formData.attack_detection.rule_lib_file_path" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="规则库备份路径">
									<a-input v-model:value="formData.attack_detection.rule_lib_backup_path" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="规则库同步间隔（秒）">
									<a-input-number v-model:value="formData.attack_detection.rule_lib_sync_interval" :min="60" :max="86400" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="流量基线采样数">
									<a-input-number v-model:value="formData.attack_detection.traffic_baseline_samples" :min="10" :max="10000" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="流量采集间隔（秒）">
									<a-input-number v-model:value="formData.attack_detection.traffic_collect_interval" :min="0.01" :max="10" :step="0.1" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="流量队列最大值">
									<a-input-number v-model:value="formData.attack_detection.traffic_queue_max_size" :min="100" :max="100000" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<!-- 攻击检测阈值 -->
					<a-card title="攻击检测阈值" :bordered="false" size="small" class="config-card">
						<a-divider orientation="left" plain>端口扫描</a-divider>
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="端口数阈值">
									<a-input-number v-model:value="formData.attack_detection.thresholds.port_scan_port_count" :min="1" :max="1000" style="width: 100%" />
									<div class="form-item-tip">同一IP在时间窗口内扫描端口数超过此值判定为扫描</div>
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="时间窗口（秒）">
									<a-input-number v-model:value="formData.attack_detection.thresholds.port_scan_time_window" :min="1" :max="600" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>

						<a-divider orientation="left" plain>暴力破解</a-divider>
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="失败次数阈值">
									<a-input-number v-model:value="formData.attack_detection.thresholds.brute_force_fail_count" :min="1" :max="100" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="时间窗口（秒）">
									<a-input-number v-model:value="formData.attack_detection.thresholds.brute_force_time_window" :min="1" :max="3600" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>

						<a-divider orientation="left" plain>DDoS 防护</a-divider>
						<a-row :gutter="16">
							<a-col :span="6">
								<a-form-item label="SYN 并发连接">
									<a-input-number v-model:value="formData.attack_detection.thresholds.ddos_syn_connections" :min="10" :max="100000" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="UDP PPS">
									<a-input-number v-model:value="formData.attack_detection.thresholds.ddos_udp_pps" :min="10" :max="1000000" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="ICMP PPS">
									<a-input-number v-model:value="formData.attack_detection.thresholds.ddos_icmp_pps" :min="10" :max="1000000" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="6">
								<a-form-item label="流量阈值（Mbps）">
									<a-input-number v-model:value="formData.attack_detection.thresholds.ddos_traffic_mbps" :min="1" :max="100000" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>

						<a-divider orientation="left" plain>流量基线</a-divider>
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="基线计算窗口（秒）">
									<a-input-number v-model:value="formData.attack_detection.thresholds.traffic_baseline_window" :min="60" :max="86400" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="突发倍数">
									<a-input-number v-model:value="formData.attack_detection.thresholds.traffic_burst_baseline_multiplier" :min="1" :max="100" :step="0.1" style="width: 100%" />
									<div class="form-item-tip">超过基线流量的此倍数判定为异常</div>
								</a-form-item>
							</a-col>
						</a-row>

						<a-divider orientation="left" plain>Web 攻击检测</a-divider>
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="检测间隔（秒）">
									<a-input-number v-model:value="formData.attack_detection.thresholds.web_attack_check_interval" :min="1" :max="600" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="告警冷却（秒）">
									<a-input-number v-model:value="formData.attack_detection.thresholds.web_attack_cooldown" :min="1" :max="3600" style="width: 100%" />
									<div class="form-item-tip">同IP同类型不重复告警</div>
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="日志增量读取（字节）">
									<a-input-number v-model:value="formData.attack_detection.thresholds.web_attack_log_tail_size" :min="1024" :max="10485760" :step="1024" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>
				</div>

				<!-- ================================================================ -->
				<!-- 步骤3：流量与日志监控                                             -->
				<!-- ================================================================ -->
				<div v-show="currentStep === 2">
					<!-- Payload 嗅探 -->
					<a-card title="Payload 流量嗅探" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="启用嗅探">
									<a-switch v-model:checked="formData.payload_sniffer.enabled" checked-children="开启" un-checked-children="关闭" />
									<div class="form-item-tip">抓取指定端口TCP流量，分析Payload攻击特征</div>
								</a-form-item>
							</a-col>
						</a-row>
						<a-form-item label="嗅探端口">
							<a-select
								v-model:value="snifferPortsTags"
								mode="tags"
								placeholder="输入端口号后按回车添加，如 80、443"
								:token-separators="[',', ' ']"
								allow-clear
								:disabled="!formData.payload_sniffer.enabled"
							/>
						</a-form-item>
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="上报间隔（秒）">
									<a-input-number v-model:value="formData.payload_sniffer.upload_interval" :min="1" :max="600" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="最大Payload（字节）">
									<a-input-number v-model:value="formData.payload_sniffer.max_payload_size" :min="256" :max="65536" :step="256" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="事件队列上限">
									<a-input-number v-model:value="formData.payload_sniffer.event_queue_max" :min="10" :max="100000" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="冷却时间（秒）">
									<a-input-number v-model:value="formData.payload_sniffer.cooldown" :min="1" :max="3600" style="width: 100%" />
									<div class="form-item-tip">同IP同类型不重复上报</div>
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<!-- 进程监控 -->
					<a-card title="进程监控" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="启用进程监控">
									<a-switch v-model:checked="formData.process_monitor.enabled" checked-children="开启" un-checked-children="关闭" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="扫描间隔（秒）">
									<a-input-number v-model:value="formData.process_monitor.scan_interval" :min="1" :max="600" style="width: 100%" :disabled="!formData.process_monitor.enabled" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="冷却时间（秒）">
									<a-input-number v-model:value="formData.process_monitor.cooldown" :min="1" :max="86400" style="width: 100%" :disabled="!formData.process_monitor.enabled" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<!-- Web 日志源 -->
					<a-card title="Web 服务器日志源" :bordered="false" size="small" class="config-card">
						<div class="form-item-tip" style="margin-bottom: 12px">
							配置Web服务器访问日志路径，系统增量读取日志分析SQL注入、XSS等攻击行为
						</div>
						<div class="web-log-section">
							<a-row
								v-for="(item, index) in formData.webLogSources"
								:key="index"
								:gutter="8"
								class="mb-2"
								align="middle"
							>
								<a-col :span="10">
									<a-input v-model:value="item.path" placeholder="日志文件或目录路径" />
								</a-col>
								<a-col :span="6">
									<a-select v-model:value="item.type" placeholder="类型">
										<a-select-option value="nginx">Nginx</a-select-option>
										<a-select-option value="apache">Apache</a-select-option>
										<a-select-option value="iis">IIS</a-select-option>
										<a-select-option value="tomcat">Tomcat</a-select-option>
										<a-select-option value="auto">自动识别</a-select-option>
									</a-select>
								</a-col>
								<a-col :span="4">
									<a-switch v-model:checked="item.enabled" checked-children="启用" un-checked-children="禁用" size="small" />
								</a-col>
								<a-col :span="4" class="text-center">
									<MinusCircleOutlined class="dynamic-delete-button" @click="removeWebLogSource(index)" />
									<PlusOutlined
										v-if="index === formData.webLogSources.length - 1"
										class="dynamic-add-button ml-2"
										@click="addWebLogSource"
									/>
								</a-col>
							</a-row>
							<a-button v-if="formData.webLogSources.length === 0" type="dashed" block @click="addWebLogSource">
								<PlusOutlined /> 添加Web日志路径
							</a-button>
						</div>
					</a-card>
				</div>

				<!-- ================================================================ -->
				<!-- 步骤4：资源限制配置                                               -->
				<!-- ================================================================ -->
				<div v-show="currentStep === 3">
					<a-card title="CPU 限制" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="峰值上限（%）">
									<a-input-number v-model:value="formData.resources.cpu_peak_limit" :min="1" :max="100" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="平均上限（%）">
									<a-input-number v-model:value="formData.resources.cpu_avg_limit" :min="1" :max="100" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="采样间隔（秒）">
									<a-input-number v-model:value="formData.resources.cpu_sample_interval" :min="1" :max="60" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="节流阈值（%）">
									<a-input-number v-model:value="formData.resources.cpu_throttle_threshold" :min="1" :max="100" style="width: 100%" />
									<div class="form-item-tip">CPU使用率超过此值时开始休眠节流</div>
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="节流休眠（秒）">
									<a-input-number v-model:value="formData.resources.cpu_throttle_sleep" :min="0.01" :max="10" :step="0.01" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<a-card title="内存限制" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="峰值上限（MB）">
									<a-input-number v-model:value="formData.resources.memory_peak_limit" :min="50" :max="4096" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="常驻上限（MB）">
									<a-input-number v-model:value="formData.resources.memory_resident_limit" :min="10" :max="2048" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="告警阈值（MB）">
									<a-input-number v-model:value="formData.resources.memory_warning_threshold" :min="50" :max="4096" style="width: 100%" />
									<div class="form-item-tip">超过时触发GC垃圾回收</div>
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<a-card title="磁盘 IO 限制" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="峰值上限（MB/s）">
									<a-input-number v-model:value="formData.resources.disk_io_peak_limit" :min="1" :max="1000" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="平均上限（MB/s）">
									<a-input-number v-model:value="formData.resources.disk_io_avg_limit" :min="1" :max="500" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="节流阈值（MB/s）">
									<a-input-number v-model:value="formData.resources.disk_io_throttle_threshold" :min="1" :max="1000" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="节流休眠（秒）">
									<a-input-number v-model:value="formData.resources.disk_io_throttle_sleep" :min="0.01" :max="10" :step="0.01" style="width: 100%" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>
				</div>

				<!-- ================================================================ -->
				<!-- 步骤5：系统参数配置                                               -->
				<!-- ================================================================ -->
				<div v-show="currentStep === 4">
					<a-card title="日志配置" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="日志级别">
									<a-select v-model:value="formData.logging.level">
										<a-select-option value="DEBUG">DEBUG</a-select-option>
										<a-select-option value="INFO">INFO</a-select-option>
										<a-select-option value="WARNING">WARNING</a-select-option>
										<a-select-option value="ERROR">ERROR</a-select-option>
									</a-select>
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="单文件最大（字节）">
									<a-input-number v-model:value="formData.logging.max_size" :min="1048576" :max="104857600" :step="1048576" style="width: 100%" />
									<div class="form-item-tip">默认 10MB = 10485760</div>
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="备份数量">
									<a-input-number v-model:value="formData.logging.backup_count" :min="1" :max="50" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="缓冲区大小（字节）">
									<a-input-number v-model:value="formData.logging.buffer_size" :min="256" :max="65536" :step="256" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="文件名前缀">
									<a-input v-model:value="formData.logging.file_prefix" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<a-card title="授权管理" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="缓存有效期（秒）">
									<a-input-number v-model:value="formData.auth.cache_ttl" :min="10" :max="86400" style="width: 100%" />
									<div class="form-item-tip">有效期内不重复验证授权状态</div>
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="离线宽限期（秒）">
									<a-input-number v-model:value="formData.auth.offline_grace_period" :min="60" :max="86400" style="width: 100%" />
									<div class="form-item-tip">网络断开后允许继续运行的时长</div>
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<a-card title="AES 加密" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="密钥长度（位）">
									<a-select v-model:value="formData.crypto.aes_key_length">
										<a-select-option :value="128">128</a-select-option>
										<a-select-option :value="192">192</a-select-option>
										<a-select-option :value="256">256</a-select-option>
									</a-select>
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="分组大小（字节）">
									<a-input-number v-model:value="formData.crypto.aes_block_size" :min="16" :max="32" style="width: 100%" disabled />
									<div class="form-item-tip">CBC模式固定为16字节</div>
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<a-card title="硬件采集" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="12">
								<a-form-item label="CPU采样间隔（秒）">
									<a-input-number v-model:value="formData.hardware.cpu_usage_sample_interval" :min="0.1" :max="10" :step="0.1" style="width: 100%" />
								</a-form-item>
							</a-col>
							<a-col :span="12">
								<a-form-item label="机器ID文件名">
									<a-input v-model:value="formData.hardware.machine_id_file" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>

					<a-card title="存储路径" :bordered="false" size="small" class="config-card">
						<a-row :gutter="16">
							<a-col :span="8">
								<a-form-item label="配置文件名">
									<a-input v-model:value="formData.storage.config_file_name" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="Windows目录名">
									<a-input v-model:value="formData.storage.config_dir_name" />
								</a-form-item>
							</a-col>
							<a-col :span="8">
								<a-form-item label="Unix目录名">
									<a-input v-model:value="formData.storage.config_dir_name_unix" />
								</a-form-item>
							</a-col>
						</a-row>
					</a-card>
				</div>
			</a-form>
		</div>

		<!-- 底部按钮 -->
		<template #footer>
			<div style="display: flex; justify-content: space-between; align-items: center">
				<div>
					<a-button @click="onDownload" :loading="downloadLoading">
						<template #icon><DownloadOutlined /></template>
						下载配置
					</a-button>
				</div>
				<div>
					<a-button v-if="currentStep > 0" style="margin-right: 8px" @click="prevStep">
						<LeftOutlined /> 上一步
					</a-button>
					<a-button v-if="currentStep < totalSteps - 1" type="primary" @click="nextStep">
						下一步 <RightOutlined />
					</a-button>
					<a-button type="primary" :loading="submitLoading" @click="onSubmit" style="margin-left: 8px">
						保存配置
					</a-button>
					<a-button style="margin-left: 8px" @click="onClose">关闭</a-button>
				</div>
			</div>
		</template>
	</xn-form-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined, MinusCircleOutlined, DownloadOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons-vue'
import ewmProjectSafeApi from '@/api/ewm/ewmProjectSafeApi'
import sysConfig from '@/config/index'

const visible = ref(false)
const formRef = ref()
const submitLoading = ref(false)
const downloadLoading = ref(false)
const currentSafeId = ref('')
const currentStep = ref(0)
const totalSteps = 5

// =========================================================================
// 默认值（与 client_config.json 的 settings + 顶层可配置项完全对齐）
// =========================================================================
const buildDefault = () => ({
	// --- settings 子节 ---
	server: {
		url: 'http://127.0.0.1:82/safe',
		project_id: '2023031623403520002',
		endpoints: {
			register: '/init/add',
			heartbeat: '/init/check',
			attack_web: '/init/attack/web',
			attack_portscan: '/init/attack/portscan',
			attack_traffic: '/init/attack/traffic',
			attack_threshold: '/attack/threshold/get',
			detector_status: '/attack/detector/status',
			rule_lib_version: '/attack/rule/version',
			rule_lib_update: '/attack/rule/update'
		}
	},
	websocket: {
		url: 'ws://127.0.0.1:82/safe/init/ws',
		reconnect_interval: 5,
		ssl_verify: true
	},
	heartbeat: {
		interval: 15,
		request_timeout: 5,
		max_retry: 5,
		retry_interval: 1
	},
	ip_blocker: {
		enabled: false,
		whitelist_sync_interval: 300,
		block_outbound: false,
		min_attack_level: 'low',
		rule_name_prefix: 'SafeClient_Block_'
	},
	attack_detection: {
		attack_log_batch_size: 50,
		attack_log_upload_interval: 30,
		attack_detector_max_restart: 10,
		attack_detector_restart_delay: 3,
		rule_lib_file_path: 'data/rule_lib.json',
		rule_lib_backup_path: 'data/rule_lib.backup.json',
		rule_lib_sync_interval: 600,
		traffic_baseline_samples: 100,
		traffic_collect_interval: 0.1,
		traffic_queue_max_size: 10000,
		thresholds: {
			port_scan_port_count: 20,
			port_scan_time_window: 10,
			brute_force_fail_count: 5,
			brute_force_time_window: 60,
			ddos_syn_connections: 1000,
			ddos_udp_pps: 10000,
			ddos_icmp_pps: 5000,
			ddos_traffic_mbps: 100,
			traffic_baseline_window: 600,
			traffic_burst_baseline_multiplier: 2.0,
			web_attack_check_interval: 10,
			web_attack_cooldown: 60,
			web_attack_log_tail_size: 65536
		}
	},
	payload_sniffer: {
		enabled: true,
		ports: [80, 443, 8080, 8443],
		upload_interval: 10,
		max_payload_size: 4096,
		event_queue_max: 1000,
		cooldown: 60
	},
	process_monitor: {
		enabled: true,
		scan_interval: 5,
		cooldown: 300
	},
	resources: {
		cpu_peak_limit: 8,
		cpu_avg_limit: 5,
		cpu_throttle_threshold: 7,
		cpu_throttle_sleep: 0.1,
		cpu_sample_interval: 5,
		memory_peak_limit: 300,
		memory_resident_limit: 100,
		memory_warning_threshold: 280,
		disk_io_peak_limit: 10,
		disk_io_avg_limit: 1,
		disk_io_throttle_threshold: 9,
		disk_io_throttle_sleep: 0.5
	},
	logging: {
		level: 'INFO',
		max_size: 10485760,
		backup_count: 5,
		buffer_size: 1024,
		file_prefix: 'client'
	},
	auth: {
		cache_ttl: 300,
		offline_grace_period: 600
	},
	crypto: {
		aes_key_length: 128,
		aes_block_size: 16
	},
	hardware: {
		cpu_usage_sample_interval: 0.5,
		machine_id_file: '.machine_id'
	},
	storage: {
		config_file_name: 'client_config.json',
		config_dir_name: 'client_config',
		config_dir_name_unix: '.client_config'
	},
	// --- 顶层可配置字段 ---
	ipWhitelist: [],
	webLogSources: []
})

const formData = ref(buildDefault())

// 嗅探端口: 数字数组 <-> 字符串标签 双向桥接
const snifferPortsTags = computed({
	get: () => (formData.value.payload_sniffer.ports || []).map(String),
	set: (tags) => {
		formData.value.payload_sniffer.ports = tags.map(Number).filter((n) => !isNaN(n) && n > 0)
	}
})

// =========================================================================
// 深度合并：把 src 递归合并到 target（已有键覆盖，缺失键保留默认）
// =========================================================================
const deepMerge = (target, src) => {
	if (!src || typeof src !== 'object') return
	for (const key of Object.keys(src)) {
		if (src[key] !== null && typeof src[key] === 'object' && !Array.isArray(src[key]) && typeof target[key] === 'object' && !Array.isArray(target[key])) {
			deepMerge(target[key], src[key])
		} else if (src[key] !== undefined && src[key] !== null) {
			target[key] = src[key]
		}
	}
}

// =========================================================================
// 打开 / 关闭
// =========================================================================
const onOpen = (record) => {
	visible.value = true
	currentStep.value = 0
	currentSafeId.value = record.id
	formData.value = buildDefault()

	ewmProjectSafeApi.getConfig({ safeId: record.id }).then((res) => {
		if (res && Object.keys(res).length > 0) {
			deepMerge(formData.value, res)
		}
	})
}

const onClose = () => {
	visible.value = false
	currentStep.value = 0
}

// 步骤导航
const nextStep = () => {
	if (currentStep.value < totalSteps - 1) currentStep.value++
}
const prevStep = () => {
	if (currentStep.value > 0) currentStep.value--
}

// Web日志源 增删
const addWebLogSource = () => {
	formData.value.webLogSources.push({ path: '', type: 'nginx', enabled: true })
}
const removeWebLogSource = (index) => {
	formData.value.webLogSources.splice(index, 1)
}

// =========================================================================
// 保存
// =========================================================================
const onSubmit = () => {
	submitLoading.value = true
	// 构建提交数据：过滤掉空路径的 webLogSources
	const config = JSON.parse(JSON.stringify(formData.value))
	config.webLogSources = (config.webLogSources || []).filter((item) => item.path)
	const params = {
		safeId: currentSafeId.value,
		config: config
	}
	ewmProjectSafeApi
		.saveConfig(params)
		.then(() => {
			message.success('配置保存成功')
		})
		.finally(() => {
			submitLoading.value = false
		})
}

// =========================================================================
// 下载
// =========================================================================
const onDownload = () => {
	downloadLoading.value = true
	const token = localStorage.getItem('TOKEN') || ''
	const url = sysConfig.API_URL + '/safe/projectsafe/config/download?safeId=' + currentSafeId.value + '&token=' + token
	const iframe = document.createElement('iframe')
	iframe.style.display = 'none'
	iframe.src = url
	document.body.appendChild(iframe)
	setTimeout(() => {
		document.body.removeChild(iframe)
		downloadLoading.value = false
	}, 3000)
}

defineExpose({ onOpen })
</script>

<style scoped>
.step-content {
	min-height: 300px;
	max-height: 60vh;
	overflow-y: auto;
	padding-right: 4px;
}
.config-card {
	margin-bottom: 12px;
}
.config-card :deep(.ant-card-head) {
	min-height: 36px;
	padding: 0 12px;
	font-size: 13px;
	background: #fafafa;
}
.config-card :deep(.ant-card-head-title) {
	padding: 6px 0;
}
.config-card :deep(.ant-card-body) {
	padding: 12px;
}
.config-card :deep(.ant-form-item) {
	margin-bottom: 10px;
}
.form-item-tip {
	color: #999;
	font-size: 12px;
	margin-top: 2px;
	line-height: 1.5;
}
.dynamic-delete-button {
	cursor: pointer;
	font-size: 20px;
	color: #999;
	transition: all 0.3s;
}
.dynamic-delete-button:hover {
	color: #ff4d4f;
}
.dynamic-add-button {
	cursor: pointer;
	font-size: 20px;
	color: #1890ff;
}
.ml-2 {
	margin-left: 8px;
}
.mb-2 {
	margin-bottom: 8px;
}
.text-center {
	text-align: center;
}
.web-log-section {
	margin-bottom: 8px;
}
</style>
