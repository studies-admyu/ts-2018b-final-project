def configParams():
    params = {}

    print("config parameters...")

    params['gpuId'] = 0
    params['data_path'] = "/media/zhang/zhang/data/"
    params['ilsvrc2015'] = params['data_path'] + "ILSVRC2015_VID/"
    params['crops_path'] = params['data_path'] + "ILSVRC2015_CROPS/"
    params['crops_train'] = params['crops_path'] + "Data/VID/train/"
    params['curation_path'] = "./ILSVRC15-curation/"
    params['seq_base_path'] = "./demo-sequences/"
    params['trainBatchSize'] = 8
    params['numScale'] = 3

    return params
