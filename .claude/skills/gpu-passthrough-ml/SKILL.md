# Skill: GPU Passthrough & ML Hardware Optimization

You are the Hardware Acceleration Specialist. You configure PCI passthrough for the ML Training Lab to ensure bare-metal GPU performance.

---

## When This Skill Applies
Activate this skill whenever:
- Configuring VM 102 (ML Lab).
- Troubleshooting GPU visibility, driver crashes, or ROCm issues.
- Managing IOMMU groups or VFIO modules.
- Optimizing PyTorch/Training performance.

---

## Host Configuration (Proxmox)

### 1. BIOS & Kernel
- **IOMMU**: Enabled (`amd_iommu=on iommu=pt`).
- **Blacklist**: `amdgpu` and `radeon` drivers MUST be blacklisted on the host.
- **Modules**: `vfio`, `vfio_iommu_type1`, `vfio_pci` loaded at boot.

### 2. VFIO Binding
- Bind GPU PCI IDs (Video + Audio) to `vfio-pci` in `/etc/modprobe.d/vfio-pci.conf`.
- **AMD Specific**: Use `vendor-reset` module to fix reset bug on VM restart.

### 3. VM Settings (VM 102)
- **Machine**: `q35`.
- **BIOS**: `OVMF` (UEFI).
- **PCI Device**: `hostpci0: 0000:xx:xx.0,pcie=1,x-vga=1`.
- **CPU Type**: `host`.

## Guest Configuration (Ubuntu VM)

### 1. Drivers & Stack
- **Stack**: AMD ROCm (version matching host compatibility).
- **Groups**: User must be in `render` and `video` groups.
- **Env Vars**: `HSA_OVERRIDE_GFX_VERSION` (if needed for consumer cards).

### 2. Verification
- `rocminfo`: Must list the GPU agent.
- `rocm-smi`: Must show temps/clocks.
- `python -c "import torch; print(torch.cuda.is_available())"`: Must return `True`.

## Validation Checklist
- [ ] Are host drivers blacklisted?
- [ ] Is `vendor-reset` active?
- [ ] Is the VM Machine Type `q35`?
- [ ] Does `rocm-smi` inside the VM show the card?
