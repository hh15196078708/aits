<template>
	<div class="xd-file-manager flex flex-col h-full bg-white rounded-md shadow-sm border border-gray-100">
		<!-- 顶部工具栏 -->
		<div class="flex flex-col md:flex-row justify-between items-center p-3 border-b border-gray-100 gap-3">
			<!-- 左侧操作区 -->
			<div class="flex gap-2 w-full md:w-auto">
				<a-button type="primary" @click="triggerUpload">
					<template #icon>
						<CloudUploadOutlined/>
					</template>
					上传文件
				</a-button>
				<a-button @click="handleCreateFolder">
					<template #icon>
						<FolderAddOutlined/>
					</template>
					新建文件夹
				</a-button>

				<!--				&lt;!&ndash; 上传队列气泡 &ndash;&gt;-->
				<!--				<a-popover v-if="uploadQueue.length > 0" title="上传队列" trigger="click" placement="bottomLeft">-->
				<!--					<template #content>-->
				<!--						<div class="w-72 max-h-60 overflow-y-auto custom-scrollbar">-->
				<!--							<div v-for="task in uploadQueue" :key="task.id" class="mb-3">-->
				<!--								<div class="flex justify-between text-xs mb-1 text-gray-600">-->
				<!--									<span class="truncate max-w-[70%]" :title="task.name">{{ task.name }}</span>-->
				<!--									<span>{{ task.status === 'done' ? '完成' : task.progress + '%' }}</span>-->
				<!--								</div>-->
				<!--								<a-progress-->
				<!--									:percent="task.progress"-->
				<!--									size="small"-->
				<!--									:status="getUploadStatus(task.status)"-->
				<!--									:show-info="false"-->
				<!--								/>-->
				<!--							</div>-->
				<!--						</div>-->
				<!--					</template>-->
				<!--					<a-button :loading="isUploading">-->
				<!--						{{ isUploading ? `正在上传 (${uploadQueue.length})` : '上传完成' }}-->
				<!--					</a-button>-->
				<!--				</a-popover>-->
			</div>

			<!-- 右侧筛选区 -->
			<div class="flex gap-2 items-center w-full md:w-auto">
				<a-input-search
					v-model:value="searchKeyword"
					placeholder="搜索文件名..."
					class="w-full md:w-56"
					@search="loadData(currentFolderId)"
					allow-clear
				/>
				<a-radio-group v-model:value="viewMode" button-style="solid">
					<a-radio-button value="list">
						列表
					</a-radio-button>
					<a-radio-button value="grid">
						图标
					</a-radio-button>
				</a-radio-group>
			</div>
		</div>

		<!-- 面包屑导航 -->
		<div
			class="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center text-sm overflow-x-auto whitespace-nowrap">
			<span class="text-gray-400 mr-2 flex-shrink-0">当前位置：</span>
			<a-breadcrumb separator="/">
				<a-breadcrumb-item>
					<a class="text-gray-600 hover:text-primary" @click="navigateTo(null)">
						<HomeOutlined/>
						根目录
					</a>
				</a-breadcrumb-item>
				<a-breadcrumb-item v-for="(folder, index) in breadcrumbStack" :key="folder.id">
					<a class="text-gray-600 hover:text-primary" @click="navigateTo(folder.id, index)">
						{{ folder.name }}
					</a>
				</a-breadcrumb-item>
			</a-breadcrumb>
		</div>

		<!-- 主内容区 -->
		<div class="flex-1 overflow-hidden relative" v-loading="loading">

			<!-- 列表视图 -->
			<div v-if="viewMode === 'list'" class="h-full overflow-y-auto">
				<a-table
					:dataSource="fileList"
					:columns="columns"
					rowKey="id"
					:pagination="{
        current: pagination.current,
        pageSize: pagination.size,
        total: pagination.total,
        showSizeChanger: true,
        showTotal: total => `共 ${total} 项`,
        onChange: handlePageChange,
        onShowSizeChange: handlePageChange
    }"
					:sticky="true"
				>

					<template #bodyCell="{ column, record }">
						<template v-if="column.key === 'name'">
							<div class="flex items-center cursor-pointer group" @click="handleItemClick(record)">
								<component
									:is="getFileIcon(record)"
									class="text-4xl mr-4 flex-shrink-0 xdfontSize"
									:class="record.isFolder ? 'text-yellow-400' : 'text-blue-400'"
								/>
								<span class="group-hover:text-primary transition-colors truncate">{{
										record.name
									}}</span>
							</div>
						</template>
						<template v-else-if="column.key === 'size'">
							<span class="text-gray-400">{{ record.isFolder ? '-' : formatSize(record.fileSize) }}</span>
						</template>
						<template v-else-if="column.key === 'updateTime'">
							<span class="text-gray-500">{{ record.updateTime || record.createTime || '-' }}</span>
						</template>
						<template v-else-if="column.key === 'action'">
							<a-space>
								<a class="text-blue-500 hover:text-blue-700" @click.stop="openRenameModal(record)">重命名</a>
								<a class="text-blue-500 hover:text-blue-700"
								   @click.stop="openMoveModal(record)">移动</a>
								<a-popconfirm title="确定要删除此文件吗？" @confirm="handleDelete(record)">
									<a class="text-red-500 hover:text-red-700">删除</a>
								</a-popconfirm>
							</a-space>
						</template>
					</template>
				</a-table>
			</div>

			<!-- 网格视图 -->
			<div v-else class="h-full overflow-y-auto p-4">
				<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-6">
					<div
						v-for="item in fileList"
						:key="item.id"
						class="group relative border border-gray-200 rounded-lg p-4 flex flex-col items-center cursor-pointer hover:shadow-md hover:border-primary hover:bg-blue-50 transition-all bg-white"
						@click="handleItemClick(item)"
					>
						<div class="text-7xl mb-4 transition-transform group-hover:scale-110">
							<component
								:is="getFileIcon(item)"
								class="xdfontSize"
								:class="item.isFolder ? 'text-yellow-400' : 'text-blue-400'"
							/>
						</div>
						<div class="text-center w-full">
							<div class="truncate text-sm font-medium text-gray-700" :title="item.name">{{
									item.name
								}}
							</div>
							<div class="text-xs text-gray-400 mt-1">
								{{ item.isFolder ? item.updateTime : formatSize(item.fileSize) }}
							</div>
						</div>

						<!-- 悬浮操作菜单 -->
						<div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
							<a-dropdown trigger="click" @click.stop>
								<a-button type="text" size="small"
										  class="bg-white/80 hover:bg-white shadow-sm rounded-full !px-1">
									<MoreOutlined/>
								</a-button>
								<template #overlay>
									<a-menu>
										<a-menu-item @click="openRenameModal(item)">重命名</a-menu-item>
										<a-menu-item @click="openMoveModal(item)">移动到...</a-menu-item>
										<a-menu-item danger @click="handleDelete(item)">删除</a-menu-item>
									</a-menu>
								</template>
							</a-dropdown>
						</div>
					</div>
				</div>
				<a-empty v-if="fileList.length === 0" description="暂无文件" class="mt-20"/>
				<div class="p-3 border-t text-right bg-white">
					<a-pagination
						v-model:current="pagination.current"
						v-model:pageSize="pagination.size"
						:total="pagination.total"
						show-size-changer
						:show-total="total => `共 ${total} 项`"
						@change="handlePageChange"
					/>
				</div>
			</div>
		</div>

		<!-- 隐藏的文件输入框 -->
		<input type="file" ref="fileInputRef" class="hidden" multiple @change="handleFileChange"/>

		<!-- 新建文件夹弹窗 -->
		<a-modal
			v-model:open="createFolderModal.visible"
			title="新建文件夹"
			@ok="handleCreateFolderSubmit"
			:confirmLoading="createFolderModal.loading"
			destroyOnClose
		>
			<a-form
				ref="createFolderFormRef"
				:model="createFolderModal.form"
				:rules="createFolderRules"
				layout="vertical"
			>
				<a-form-item label="文件夹名称" name="name">
					<a-input v-model:value="createFolderModal.form.name" placeholder="请输入文件夹名称" allow-clear/>
				</a-form-item>
				<a-form-item label="排序" name="sortCode">
					<a-input-number v-model:value="createFolderModal.form.sortCode" class="w-full"
									placeholder="请输入排序号" :min="0" :step="1"/>
				</a-form-item>
			</a-form>
		</a-modal>

		<!-- 移动文件弹窗 -->
		<a-modal
			v-model:open="moveModal.visible"
			title="移动文件"
			@ok="handleMoveSubmit"
			:confirmLoading="moveModal.loading"
			destroyOnClose
		>
			<a-form layout="vertical">
				<a-form-item label="当前选中文件">
					<a-input disabled :value="moveModal.currentItem?.name"/>
				</a-form-item>
				<a-form-item label="选择目标文件夹">
					<a-tree-select
						v-model:value="moveModal.targetId"
						style="width: 100%"
						:dropdown-style="{ maxHeight: '400px', overflow: 'auto' }"
						placeholder="请选择目标文件夹"
						allow-clear
						tree-default-expand-all
						show-search
						tree-node-filter-prop="name"
						:tree-data="moveModal.treeData"
						:load-data="onLoadFolderData"
						:fieldNames="{ children: 'children', label: 'name', value: 'id' }"
					>
						<template #title="{ name }">
							<FolderOutlined class="text-yellow-400 mr-1"/>
							{{ name }}
						</template>
					</a-tree-select>
				</a-form-item>
			</a-form>
		</a-modal>
		<a-modal
			v-model:open="uploadProgressModal.visible"
			title="文件上传中"
			:footer="null"
			:closable="false"
			:maskClosable="false"
			destroyOnClose
		>
			<div class="py-4">
				<div v-for="task in uploadQueue" :key="task.id" class="mb-6 last:mb-0">
					<div class="flex justify-between mb-2">
           <span class="font-medium truncate max-w-[80%]" :title="task.name">
              {{ task.name }}
           </span>
						<span class="text-gray-500 text-xs">
              {{ task.status === 'done' ? '已完成' : (task.status === 'error' ? '失败' : task.progress + '%') }}
           </span>
					</div>
					<div class="text-xs text-gray-400 mb-1">
						{{ task.statusText }}
					</div>
					<a-progress
						:percent="task.progress"
						:status="getUploadStatus(task.status)"
						:stroke-color="task.status === 'done' ? '#52c41a' : ''"
					/>
				</div>
			</div>
		</a-modal>
		<a-modal
			v-model:open="renameModal.visible"
			title="重命名"
			@ok="handleRenameSubmit"
			:confirmLoading="renameModal.loading"
			destroyOnClose
		>
			<a-form layout="vertical">
				<a-form-item label="名称" required>
					<a-input v-model:value="renameModal.newName" placeholder="请输入新名称" allow-clear />
				</a-form-item>
			</a-form>
		</a-modal>
	</div>
</template>

<script setup name="XdFileManager">
import SparkMD5 from 'spark-md5';
import {ref, computed, onMounted} from 'vue';
import {message, Modal} from 'ant-design-vue';
// 引入 Ant Design 图标
import {
	CloudUploadOutlined, FolderAddOutlined, HomeOutlined,
	MoreOutlined,
	FolderOutlined, FolderOpenOutlined, FileOutlined,
	FileImageOutlined, FilePdfOutlined, FileWordOutlined,
	FileExcelOutlined, FilePptOutlined, FileTextOutlined,
	FileZipOutlined, FileMarkdownOutlined
} from '@ant-design/icons-vue';
// 引入 API
import fileApi from '@/api/file';

// --- 上传配置 ---
const CHUNK_SIZE = 5 * 1024 * 1024; // 增加到 5MB 提升效率
const MAX_CONCURRENT = 3; // 最大并发上传数
// --- 状态定义 ---
const loading = ref(false);
const fileList = ref([]);
const currentFolderId = ref(0);
const breadcrumbStack = ref([]); // 面包屑栈 {id, name}
const searchKeyword = ref('');
const viewMode = ref('list'); // 'list' | 'grid'
const fileInputRef = ref(null);
// 分页状态
const pagination = ref({
	current: 1,
	size: 20,
	total: 0
});
// 重命名模态框
const renameModal = ref({
	visible: false,
	loading: false,
	currentItem: null,
	newName: ''
});
// --- 进度弹窗状态 ---
const uploadProgressModal = ref({
	visible: false
});
// 上传队列
const uploadQueue = ref([]); // { id, name, progress, status: 'uploading'|'done'|'error', file }
const isUploading = computed(() => uploadQueue.value.some(t => t.status === 'uploading'));

// 新建文件夹模态框
const createFolderFormRef = ref();
const createFolderModal = ref({
	visible: false,
	loading: false,
	form: {
		name: '',
		sortCode: 99
	}
});
const createFolderRules = {
	name: [{required: true, message: '请输入文件夹名称', trigger: 'blur'}]
};

// 移动模态框
const moveModal = ref({
	visible: false,
	loading: false,
	currentItem: null,
	targetId: null,
	treeData: []
});

// 表格列定义
const columns = [
	{title: '文件名', dataIndex: 'name', key: 'name', width: '50%'},
	{title: '大小', dataIndex: 'fileSize', key: 'size', width: '15%'},
	{title: '修改时间', dataIndex: 'updateTime', key: 'updateTime', width: '25%'},
	{title: '操作', key: 'action', width: '10%', align: 'center'}
];

// --- 初始化 ---
onMounted(() => {
	loadData();
});

// --- 数据加载 ---
const loadData = async (parentId = '0', searchKeyword = null) => {
	loading.value = true;
	const searchForm = ref({
		parentId: parentId,
		searchKeyword: searchKeyword,
		current: pagination.value.current,
		size: pagination.value.size
	})
	try {
		const res = await fileApi.getList(searchForm.value);
		// 兼容处理：假设后端返回的是分页对象 { records: [], total: 100 }
		if (res && res.records) {
			fileList.value = res.records.sort((a, b) => {
				if (a.isFolder === b.isFolder) return 0;
				return a.isFolder ? -1 : 1;
			});
			pagination.value.total = res.total;
		} else if (Array.isArray(res)) {
			// 如果后端返回的是纯数组（未分页），则前端模拟分页
			fileList.value = res;
			pagination.value.total = res.length;
		}
	} catch (error) {
		console.error(error);
		message.error('加载文件列表失败');
	} finally {
		loading.value = false;
	}
};
// 打开重命名弹窗
const openRenameModal = (record) => {
	renameModal.value.currentItem = record;
	renameModal.value.newName = record.name; // 初始值为原文件名
	renameModal.value.visible = true;
};
// 提交重命名请求
const handleRenameSubmit = async () => {
	if (!renameModal.value.newName || renameModal.value.newName.trim() === '') {
		message.warning('名称不能为空');
		return;
	}
	// 如果名称没变，直接关闭
	if (renameModal.value.newName === renameModal.value.currentItem.name) {
		renameModal.value.visible = false;
		return;
	}

	renameModal.value.loading = true;
	try {
		// 调用后端接口更新文件名
		// 注意：后端需要支持按 ID 更新 name 字段
		await fileApi.edit({
			id: renameModal.value.currentItem.id,
			name: renameModal.value.newName,
			parentId: currentFolderId.value
		});
		message.success('重命名成功');
		renameModal.value.visible = false;
		loadData(currentFolderId.value);
	} catch (error) {
		console.error(error);
		message.error('重命名失败');
	} finally {
		renameModal.value.loading = false;
	}
};
// 处理页码改变
const handlePageChange = (page, pageSize) => {
	pagination.value.current = page;
	pagination.value.size = pageSize;
	loadData(currentFolderId.value);
};
// --- 导航操作 ---
const navigateTo = (folderId, index = -1) => {
	searchKeyword.value = '';
	currentFolderId.value = folderId;
	// searchKeyword.value = '';
	pagination.value.current = 1; // 重置页码

	if (index === -1) {
		// 回到根目录
		breadcrumbStack.value = [];
	} else {
		// 回到中间某一级
		breadcrumbStack.value = breadcrumbStack.value.slice(0, index + 1);
	}

	loadData(folderId === null ? '0' : folderId);
};

const handleItemClick = (item) => {
	if (item.isFolder) {
		// 进入文件夹
		breadcrumbStack.value.push({id: item.id, name: item.name});
		currentFolderId.value = item.id;
		searchKeyword.value = ''; // 清空搜索以便查看文件夹内容
		pagination.value.current = 1; // 重置页码
		loadData(item.id);
	} else {
		// 预览文件 (这里简单提示，实际可调用 preview 接口)
		message.info(`选中文件：${item.name}`);
	}
};

// --- 新建文件夹 ---
const handleCreateFolder = () => {
	createFolderModal.value.form = {
		name: '',
		sortCode: 99
	};
	createFolderModal.value.visible = true;
};

const handleCreateFolderSubmit = () => {
	createFolderFormRef.value.validate().then(() => {
		createFolderModal.value.loading = true;
		fileApi.createFolder({
			name: createFolderModal.value.form.name,
			sortCode: createFolderModal.value.form.sortCode,
			parentId: currentFolderId.value
		}).then(() => {
			message.success('创建成功');
			createFolderModal.value.visible = false;
			loadData(currentFolderId.value);
		}).catch(error => {
			message.error(error.message || '创建失败');
		}).finally(() => {
			createFolderModal.value.loading = false;
		});
	});
};

// --- 上传逻辑 (分片上传) ---
const triggerUpload = () => {
	fileInputRef.value.click();
};

const handleFileChange = async (e) => {
	const files = Array.from(e.target.files);
	if (!files.length) return;

	// 清空之前的队列并显示弹窗
	uploadQueue.value = [];
	uploadProgressModal.value.visible = true;
	const uploadPromises = [];
	for (const file of files) {
		const task = ref({
			id: Date.now() + Math.random(),
			name: file.name,
			progress: 0,
			status: 'uploading'
		});
		uploadQueue.value.push(task.value);
		uploadPromises.push(processUpload(file, task));
		// processUpload(file, task);
	}
	// 等待所有任务完成（无论成功失败）
	await Promise.allSettled(uploadPromises);

	// 延迟 1.5 秒自动关闭弹窗，给用户看一眼“已完成”状态的时间
	setTimeout(() => {
		// 检查是否还有正在进行的任务（防止关闭时又有新任务进来）
		if (!uploadQueue.value.some(t => t.status === 'uploading')) {
			uploadProgressModal.value.visible = false;
		}
	}, 1500);

	e.target.value = '';
};
// 修改计算 MD5 方法以更新进度文字
const computeMD5 = (file, taskRef) => {
	return new Promise((resolve, reject) => {
		taskRef.value.statusText = '正在校验文件安全性...';
		const blobSlice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
		const chunks = Math.ceil(file.size / CHUNK_SIZE);
		let currentChunk = 0;
		const spark = new SparkMD5.ArrayBuffer();
		const fileReader = new FileReader();

		fileReader.onload = (e) => {
			spark.append(e.target.result);
			currentChunk++;
			// MD5 计算进度占总进度的 5% (可选)
			taskRef.value.progress = Math.floor((currentChunk / chunks) * 5);
			if (currentChunk < chunks) {
				loadNext();
			} else {
				resolve(spark.end());
			}
		};

		fileReader.onerror = () => reject('文件读取失败');

		const loadNext = () => {
			const start = currentChunk * CHUNK_SIZE;
			const end = start + CHUNK_SIZE >= file.size ? file.size : start + CHUNK_SIZE;
			fileReader.readAsArrayBuffer(blobSlice.call(file, start, end));
		};
		loadNext();
	});
};

// --- 分片上传核心逻辑 ---
// 修改 processUpload
const processUpload = async (file, taskRef) => {
	try {
		// 1. 计算 MD5
		const fileHash = await computeMD5(file, taskRef);

		//2. 调用后端检查接口
		taskRef.value.statusText = '秒传校验中...';
		const checkRes = await fileApi.checkFile({ hash: fileHash, parentId: currentFolderId.value });
		const resultData = checkRes.data || checkRes;

		if (resultData.needUpload === false) {
			taskRef.value.progress = 100;
			taskRef.value.status = 'done';
			taskRef.value.statusText = '文件已存在，秒传成功！';
			loadData(currentFolderId.value);
			return;
		}

		const uploadedChunks = resultData.uploadedChunks || [];
		const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

		// 3. 循环上传缺失的分片
		for (let i = 0; i < totalChunks; i++) {
			if (uploadedChunks.includes(i)) continue;

			taskRef.value.statusText = `正在上传分片 (${i + 1}/${totalChunks})...`;
			const start = i * CHUNK_SIZE;
			const end = Math.min(file.size, start + CHUNK_SIZE);
			const chunkBlob = file.slice(start, end);

			const formData = new FormData();
			formData.append('chunk', chunkBlob);
			formData.append('hash', fileHash);
			formData.append('index', i);

			await fileApi.uploadChunk(formData);

			// 上传进度：从 5% 到 95%
			taskRef.value.progress = 5 + Math.floor((i / totalChunks) * 90);
		}

		// 4. 合并请求
		taskRef.value.statusText = '分片上传完成，正在合并文件...';
		await fileApi.mergeChunks({
			hash: fileHash,
			fileName: file.name,
			parentId: String(currentFolderId.value || '0')
		});

		taskRef.value.progress = 100;
		taskRef.value.status = 'done';
		taskRef.value.statusText = '文件上传并合并成功！';
		loadData(currentFolderId.value);

	} catch (error) {
		console.error(error);
		taskRef.value.status = 'error';
		taskRef.value.statusText = '上传失败：' + (error.message || '网络异常');
		message.error(`${file.name} 上传失败`);
	}
};

// --- 删除逻辑 ---
const handleDelete = async (record) => {
	try {
		const deleteForm = ref({
			id: record.id,
		})
		await fileApi.deleteFile(deleteForm.value);
		message.success('删除成功');
		loadData(currentFolderId.value);
	} catch (error) {
		message.error('删除失败');
	}
};

// --- 移动逻辑 ---
const openMoveModal = async (record) => {

	moveModal.value.currentItem = record;
	moveModal.value.visible = true;
	moveModal.value.targetId = null;
	moveModal.value.loading = true; // 开启小 loading

	// 初始化根节点
	const rootNode = { id: '0', name: '根目录', value: '0', key: '0', isLeaf: false, children: [] };

	try {
		const treeFrom = ref({
			parentId: '0',
			isFolder: 1
		})
		// 预加载第一层文件夹
		const res = await fileApi.getList(treeFrom.value);
		const list = Array.isArray(res) ? res : (res.records || []);

		// 过滤：只要文件夹，且排除掉当前正在移动的文件夹自己
		rootNode.children = list
			.filter(item => item.isFolder && item.id !== record.id)
			.map(item => ({
				id: item.id,
				value: item.id,
				key: item.id,
				name: item.name,
				isLeaf: false // 标记为非叶子节点，以便点击时触发 onLoadFolderData
			}));

		moveModal.value.treeData = [rootNode];
	} catch (error) {
		message.error('加载目录结构失败');
	} finally {
		moveModal.value.loading = false;
	}
};

const onLoadFolderData = (treeNode) => {
	return new Promise(async (resolve) => {
		// 如果已经有子数据了，不再重复加载
		if (treeNode.dataRef.children && treeNode.dataRef.children.length > 0) {
			resolve();
			return;
		}

		try {
			const treeFrom = ref({
				parentId: treeNode.dataRef.id,
				isFolder: 1
			})
			const res = await fileApi.getList(treeFrom.value);
			const list = Array.isArray(res) ? res : (res.records || []);

			const folders = list
				.filter(item => item.isFolder && item.id !== moveModal.value.currentItem?.id)
				.map(item => ({
					id: item.id,
					value: item.id,
					key: item.id,
					name: item.name,
					isLeaf: false // 继续允许向下探索
				}));

			// 如果该文件夹下没有子文件夹了，标记为叶子节点
			if (folders.length === 0) {
				treeNode.dataRef.isLeaf = true;
			} else {
				treeNode.dataRef.children = folders;
			}

			moveModal.value.treeData = [...moveModal.value.treeData];
			resolve();
		} catch (e) {
			console.error('懒加载目录失败', e);
			resolve();
		}
	});
};


const handleMoveSubmit = async () => {
	if (!moveModal.value.targetId) {
		message.warning('请选择目标文件夹');
		return;
	}

	const targetId = moveModal.value.targetId;
	const currentItem = moveModal.value.currentItem;

	// 1. 安全校验：不能移动到文件所在的当前目录
	// 如果 parentId 为空或 undefined，视为根目录 '0'
	const currentParentId = currentItem.parentId || '0';
	if (targetId === currentParentId) {
		message.warning('文件已在目标目录下，无需移动');
		return;
	}

	// 2. 如果移动的是文件夹，不能移动到它自己下面 (前端 TreeSelect 已经通过 filter 过滤了，这里是双重保险)
	if (targetId === currentItem.id) {
		message.warning('无法移动到自身内部');
		return;
	}

	moveModal.value.loading = true;
	try {
		// 根据你的后端接口定义传参，通常是 edit 接口或专门的 move 接口
		// 这里以你之前的 edit 逻辑为例，如果后端有专门的 moveFile 接口更好
		await fileApi.move({
			id: currentItem.id,
			parentId: targetId
		});

		message.success('移动成功');
		moveModal.value.visible = false;
		loadData(currentFolderId.value);
	} catch (error) {
		console.error(error);
		message.error('移动失败');
	} finally {
		moveModal.value.loading = false;
	}
};

// --- 工具函数 ---
const formatSize = (size) => {
	if (size === undefined || size === null) return '0 B';
	if (size < 1024) return size + ' B';
	else if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB';
	else if (size < 1024 * 1024 * 1024) return (size / 1024 / 1024).toFixed(2) + ' MB';
	else return (size / 1024 / 1024 / 1024).toFixed(2) + ' GB';
};

const getFileIcon = (file) => {
	if (file.isFolder) return file.id === currentFolderId.value ? FolderOpenOutlined : FolderOutlined;
	const name = file.name.toLowerCase();
	if (name.endsWith('.jpg') || name.endsWith('.png') || name.endsWith('.gif')) return FileImageOutlined;
	if (name.endsWith('.pdf')) return FilePdfOutlined;
	if (name.endsWith('.doc') || name.endsWith('.docx')) return FileWordOutlined;
	if (name.endsWith('.xls') || name.endsWith('.xlsx')) return FileExcelOutlined;
	if (name.endsWith('.ppt') || name.endsWith('.pptx')) return FilePptOutlined;
	if (name.endsWith('.txt')) return FileTextOutlined;
	if (name.endsWith('.zip') || name.endsWith('.rar')) return FileZipOutlined;
	if (name.endsWith('.md')) return FileMarkdownOutlined;
	return FileOutlined;
};

const getUploadStatus = (status) => {
	if (status === 'error') return 'exception';
	if (status === 'done') return 'success';
	return 'active';
};
</script>

<style lang="less" scoped>
.xdfontSize{
	font-size: 40px;
}
.xd-file-manager {
	/* 自定义滚动条样式 */

	.custom-scrollbar {
		&::-webkit-scrollbar {
			width: 6px;
		}

		&::-webkit-scrollbar-track {
			background: #f1f1f1;
		}

		&::-webkit-scrollbar-thumb {
			background: #ccc;
			border-radius: 3px;
		}

		&::-webkit-scrollbar-thumb:hover {
			background: #aaa;
		}
	}
}
</style>
