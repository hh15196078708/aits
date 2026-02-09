package vip.xiaonuo.ewm.modular.project.controller;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vip.xiaonuo.common.pojo.CommonResult;

@RestController
public class SafeToolsController {

    @RequestMapping("/safe/test/1")
    public String test1() {
        return "1";
    }

    @RequestMapping("/safe/auth")
    public CommonResult<String> auth() {
        return CommonResult.ok("authorized");
    }
}
