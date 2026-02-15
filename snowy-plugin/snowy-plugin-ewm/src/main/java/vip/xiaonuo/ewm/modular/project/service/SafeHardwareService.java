package vip.xiaonuo.ewm.modular.project.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import vip.xiaonuo.ewm.modular.project.entity.SafeHardware;
import vip.xiaonuo.ewm.modular.project.repository.SafeHardwareRepository;

@Service
public class SafeHardwareService {

    @Autowired
    private SafeHardwareRepository safeHardwareRepository;

    public SafeHardware save(SafeHardware safeHardware) {
        return safeHardwareRepository.save(safeHardware);
    }
}
