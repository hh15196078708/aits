import { baseRequest } from '@/utils/request'

const request = (url, ...arg) => baseRequest(`/ewm/client/` + url, ...arg)

/**
 * 客户管理 Api 接口管理器
 *
 * @author Snowy
 * @date 2024-05-20
 */
export default {
	// 获取客户分页
	ewmClientPage(data) {
		return request('page', data, 'get')
	},
	// 提交表单 edit为true时为编辑，默认为新增
	ewmClientSubmitForm(data, edit = false) {
		return request(edit ? 'edit' : 'add', data)
	},
	// 删除客户
	ewmClientDelete(data) {
		return request('delete', data)
	},
	// 获取客户详情
	ewmClientDetail(data) {
		return request('detail', data, 'get')
	}
}
