<template>
	<a-modal
		v-model:visible="visible"
		title="地图坐标拾取 (支持关键词搜索)"
		:width="900"
		:destroy-on-close="true"
		@ok="handleOk"
		@cancel="handleCancel"
	>
		<div class="map-container">
			<!-- 搜索框 -->
			<div class="search-box">
				<a-input-search
					id="map-keyword-search"
					v-model:value="searchKeyword"
					placeholder="输入关键词搜索地址..."
					style="width: 300px"
					allow-clear
				/>
				<div class="tip-text" v-if="currentPoint.lat">
					当前选中: [{{ currentPoint.lng }}, {{ currentPoint.lat }}]
					<span v-if="currentAddress"> - {{ currentAddress }}</span>
				</div>
			</div>
			<!-- 地图容器 -->
			<div id="amap-container" style="height: 500px; width: 100%"></div>
		</div>
	</a-modal>
</template>

<script setup>
import { ref, watch, nextTick, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import AMapLoader from '@amap/amap-jsapi-loader'

// 定义属性
const props = defineProps({
	// 传入的经纬度，用于回显 { longitude: '', latitude: '' }
	modelValue: {
		type: Object,
		default: () => ({ longitude: null, latitude: null })
	}
})

// 定义事件
const emit = defineEmits(['update:modelValue', 'ok'])

// 状态变量
const visible = ref(false)
const searchKeyword = ref('')
const currentPoint = ref({ lng: null, lat: null })
const currentAddress = ref('')
let map = null
let marker = null
let autoComplete = null
let placeSearch = null
let geocoder = null

// 高德地图 Key 配置 (建议放到全局配置文件中，此处为了演示直接写)
const MAP_KEY = 'ad3dc7259da265724b251b51441263aa' // ⚠️ 请替换为您的高德地图Key
const SECURITY_CODE = '81c2d4cf96baca217f54b335ddc6ce2f' // ⚠️ 如果使用了安全密钥，请替换

// 打开弹窗
const open = () => {
	visible.value = true
	// 如果有传入值，进行初始化
	if (props.modelValue && props.modelValue.longitude) {
		currentPoint.value = {
			lng: props.modelValue.longitude,
			lat: props.modelValue.latitude
		}
	} else {
		currentPoint.value = { lng: null, lat: null }
		currentAddress.value = ''
		searchKeyword.value = ''
	}

	nextTick(() => {
		initMap()
	})
}

// 关闭弹窗
const handleCancel = () => {
	visible.value = false
	destroyMap()
}

// 确认选择
const handleOk = () => {
	if (!currentPoint.value.lng) {
		message.warning('请先在地图上选择一个点')
		return
	}
	// 触发事件返回数据
	emit('ok', {
		longitude: currentPoint.value.lng,
		latitude: currentPoint.value.lat,
		address: currentAddress.value
	})
	visible.value = false
}

// 初始化地图
const initMap = () => {
	// 设置安全密钥
	window._AMapSecurityConfig = {
		securityJsCode: SECURITY_CODE,
	}

	AMapLoader.load({
		key: MAP_KEY,
		version: '2.0',
		plugins: ['AMap.AutoComplete', 'AMap.PlaceSearch', 'AMap.Geocoder', 'AMap.ToolBar']
	})
		.then((AMap) => {
			// 1. 创建地图
			map = new AMap.Map('amap-container', {
				zoom: 13,
				resizeEnable: true
			})

			map.addControl(new AMap.ToolBar())

			// 2. 如果有初始坐标，设置中心点和Marker
			if (currentPoint.value.lng) {
				const position = [currentPoint.value.lng, currentPoint.value.lat]
				map.setCenter(position)
				addMarker(position)
				// 逆地理编码获取地址
				getAddress(position)
			}

			// 3. 绑定地图点击事件
			map.on('click', (e) => {
				const lng = e.lnglat.getLng()
				const lat = e.lnglat.getLat()
				currentPoint.value = { lng, lat }
				addMarker([lng, lat])
				getAddress([lng, lat])
			})

			// 4. 初始化搜索插件
			const autoOptions = {
				input: 'map-keyword-search' // 绑定搜索框ID
			}
			autoComplete = new AMap.AutoComplete(autoOptions)
			placeSearch = new AMap.PlaceSearch({
				map: map
			})

			// 5. 绑定搜索选中事件
			autoComplete.on('select', (e) => {
				placeSearch.setCity(e.poi.adcode)
				placeSearch.search(e.poi.name, (status, result) => {
					// 搜索成功后，如果只有一个结果或想自动选中第一个结果
					if (status === 'complete' && result.poiList.pois && result.poiList.pois.length > 0) {
						const poi = result.poiList.pois[0];
						const lng = poi.location.lng;
						const lat = poi.location.lat;

						// 更新状态
						currentPoint.value = { lng, lat }
						// 添加标记
						addMarker([lng, lat])
						// 设置当前地址名称
						currentAddress.value = poi.name;
					}
				})
			})

			// 6. 初始化地理编码插件
			geocoder = new AMap.Geocoder({
				city: '全国',
				radius: 1000
			})

		})
		.catch((e) => {
			console.error(e)
			message.error('地图加载失败，请检查Key配置')
		})
}

// 添加/更新标记
const addMarker = (position) => {
	if (marker) {
		marker.setPosition(position)
	} else {
		// eslint-disable-next-line no-undef
		marker = new AMap.Marker({
			position: position,
			map: map
		})
	}
}

// 逆地理编码（经纬度 -> 地址）
const getAddress = (position) => {
	if (!geocoder) return
	geocoder.getAddress(position, (status, result) => {
		if (status === 'complete' && result.regeocode) {
			currentAddress.value = result.regeocode.formattedAddress
		}
	})
}

// 销毁地图
const destroyMap = () => {
	if (map) {
		map.destroy()
		map = null
	}
}

// 暴露方法给父组件
defineExpose({
	open
})
</script>

<style scoped>
.map-container {
	position: relative;
}
.search-box {
	position: absolute;
	top: 20px;
	left: 20px;
	z-index: 100;
	background: rgba(255, 255, 255, 0.9);
	padding: 10px;
	border-radius: 4px;
	box-shadow: 0 2px 6px rgba(0,0,0,0.1);
	display: flex;
	flex-direction: column;
	gap: 8px;
}
.tip-text {
	font-size: 12px;
	color: #666;
	max-width: 300px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
</style>
