import gradio as gr

from extensions.sd_dreambooth_extension.dreambooth.dreambooth import load_model_params
from extensions.sd_dreambooth_extension.dreambooth.utils import get_db_models, list_attention, list_floats, get_lora_models
from modules import script_callbacks, shared
from modules.ui import gr_show, create_refresh_button
import json
import requests
import os
import uuid

training_instance_types = [
    'ml.p2.xlarge',
        'ml.p2.8xlarge',
        'ml.p2.16xlarge',
        'ml.p3.2xlarge',
        'ml.p3.8xlarge',
        'ml.p3.16xlarge',
        'ml.g4dn.xlarge',
        'ml.g4dn.2xlarge',
        'ml.g4dn.4xlarge',
        'ml.g4dn.8xlarge',
        'ml.g4dn.12xlarge',
        'ml.g4dn.16xlarge'
    ]

def on_ui_tabs():
    with gr.Blocks() as dreambooth_interface:
        with gr.Row().style(equal_height=False):
            with gr.Column(variant="panel"):
                with gr.Tab("Model"):
                    db_create_new_db_model = gr.Checkbox(label="Create new model", value=True)

                    with gr.Box(visible=False) as select_existing_model_box:
                        gr.HTML(value="<p style='margin-bottom: 1.5em'><b>Select existing model</b></p>")
                        with gr.Row():
                            db_model_name = gr.Dropdown(label='Model', choices=sorted(get_db_models()))
                            create_refresh_button(db_model_name, get_db_models, lambda: {"choices": sorted(get_db_models())}, "refresh_db_models")

                        gr.HTML(value="<p style='margin: 3em'></p>")
                        with gr.Row():
                            with gr.Column():
                                gr.HTML(value="Loaded Model:")
                                db_model_path = gr.HTML()
                            with gr.Column():
                                gr.HTML(value="Model Revision:")
                                db_revision = gr.HTML(elem_id="db_revision")
                            with gr.Column():
                                gr.HTML(value="V2 Model:")
                                db_v2 = gr.HTML(elem_id="db_v2")
                            with gr.Column():
                                gr.HTML(value="Has EMA:")
                                db_has_ema = gr.HTML(elem_id="db_has_ema")
                            with gr.Column():
                                gr.HTML(value="Source Checkpoint:")
                                db_src = gr.HTML()
                            with gr.Column():
                                gr.HTML(value="Scheduler:")
                                db_scheduler = gr.HTML()

                    with gr.Box() as create_new_model_box:
                        gr.HTML(value="<p style='margin-bottom: 1.5em'><b>Create new model</b></p>")

                        db_new_model_name = gr.Textbox(label="Name")
                        db_create_from_hub = gr.Checkbox(label="Import Model from Huggingface Hub", value=False)
                        with gr.Row(visible=False) as hub_row:
                            db_new_model_url = gr.Textbox(label="Model Path", placeholder="runwayml/stable-diffusion-v1-5")
                            db_new_model_token = gr.Textbox(label="HuggingFace Token", value="")
                        with gr.Row() as local_row:
                            db_new_model_src = gr.Dropdown(label='Source Checkpoint', choices=sorted(get_sd_models()))
                            create_refresh_button(db_new_model_src, get_sd_models, lambda: {"choices": sorted(get_sd_models())}, "refresh_sd_models")
                        db_new_model_extract_ema = gr.Checkbox(label='Extract EMA Weights', value=False)
                        db_new_model_scheduler = gr.Dropdown(label='Scheduler', choices=["pndm", "lms", "euler", "euler-ancestral", "dpm", "ddim"], value="ddim")

                    def swap_model_box_visibility(db_create_new_model):
                        return {
                            select_existing_model_box: gr.update(visible=not db_create_new_model),
                            create_new_model_box: gr.update(visible=db_create_new_model)
                        }

                    db_create_new_db_model.change(
                        fn=swap_model_box_visibility,
                        inputs=[db_create_new_db_model],
                        outputs=[select_existing_model_box, create_new_model_box],
                    )

                    with gr.Row():
                        db_lora_model_name = gr.Dropdown(label='Lora Model', choices=sorted(get_lora_models()))
                        create_refresh_button(db_lora_model_name, get_lora_models, lambda: {"choices": sorted(get_lora_models())}, "refresh_lora_models")
                    db_custom_model_name = gr.Textbox(label="Custom Model Name", value="", placeholder="Enter a model name for saving checkpoints and lora models.")
                    db_lora_weight = gr.Slider(label="Lora Weight", value=1, minimum=0.1, maximum=1, step=0.1)
                    db_lora_txt_weight = gr.Slider(label="Lora Text Weight", value=1, minimum=0.1, maximum=1, step=0.1)
                    db_half_model = gr.Checkbox(label="Half Model", value=False)
                    db_use_subdir = gr.Checkbox(label="Save Checkpoint to Subdirectory", value=False)

                    with gr.Row():
                        db_train_wizard_person = gr.Checkbox(label="Optimization for training Person", value=False)
                        db_train_wizard_object = gr.Checkbox(label="Optimization for training Object/Style", value=True)
                        db_performance_wizard = gr.Checkbox(label="Optimzation for training performance (WIP)", value=True)

                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.HTML(value="")
                        with gr.Column():
                            db_create_model = gr.Button(value="Create", variant='primary', visible=False)
                with gr.Tab("Parameters"):
                    with gr.Accordion(open=True, label="Settings"):
                        with gr.Column():
                            gr.HTML(value="SageMaker")
                            db_training_instance_type = gr.Dropdown(label='Instance type', value="ml.g4dn.xlarge", choices=training_instance_types)
                            db_training_instance_count = gr.Number(label='Instance count', value=1, precision=0)
                            db_concepts_s3uri = gr.Textbox(label='Concepts S3 URI')
                            db_models_s3uri = gr.Textbox(label='Models S3 URI')

                        with gr.Column():
                            gr.HTML(value="Intervals")
                            db_num_train_epochs = gr.Number(label="Training Steps Per Image (Epochs)", precision=0, value=100)
                            db_max_train_steps = gr.Number(label='Max Training Steps', value=0, precision=0)
                            db_epoch_pause_frequency = gr.Number(label='Pause After N Epochs', value=0)
                            db_epoch_pause_time = gr.Number(label='Amount of time to pause between Epochs, in Seconds', value=60)
                            db_save_use_global_counts = gr.Checkbox(label='Use Lifetime Steps/Epochs When Saving', value=True)
                            db_save_use_epochs = gr.Checkbox(label="Save Preview/Ckpt Every Epoch")
                            db_save_embedding_every = gr.Number(label='Save Checkpoint Frequency', value=500, precision=0)
                            db_save_preview_every = gr.Number(label='Save Preview(s) Frequency', value=500, precision=0)

                        with gr.Column():
                            gr.HTML(value="Batch")
                            db_train_batch_size = gr.Number(label="Batch Size", precision=0, value=1)
                            db_sample_batch_size = gr.Number(label="Class Batch Size", precision=0, value=1)

                        with gr.Column():
                            gr.HTML(value="Learning Rate")
                            db_learning_rate = gr.Number(label='Learning Rate', value=2e-6)
                            db_lora_learning_rate = gr.Number(label='Lora unet Learning Rate', value=2e-4)
                            db_lora_txt_learning_rate = gr.Number(label='Lora Text Encoder Learning Rate', value=2e-4)
                            db_scale_lr = gr.Checkbox(label="Scale Learning Rate", value=False)
                            db_lr_scheduler = gr.Dropdown(label="Learning Rate Scheduler", value="constant", choices=["linear", "cosine", "cosine_with_restarts","polynomial", "constant", "constant_with_warmup"])
                            db_lr_warmup_steps = gr.Number(label="Learning Rate Warmup Steps", precision=0, value=500)

                        with gr.Column():
                            gr.HTML(value="Image Processing")
                            db_resolution = gr.Number(label="Resolution", precision=0, value=512)
                            db_center_crop = gr.Checkbox(label="Center Crop", value=False)
                            db_hflip = gr.Checkbox(label="Apply Horizontal Flip", value=True)
                            db_save_class_txt = gr.Checkbox(label="Save Class Captions to txt", value=True, visible=False)

                        with gr.Column():
                            gr.HTML(value="Miscellaneous")
                            db_pretrained_vae_name_or_path = gr.Textbox(label='Pretrained VAE Name or Path', placeholder="Leave blank to use base model VAE.", value="")
                            db_use_concepts = gr.Checkbox(label="Use Concepts List", value=False)
                            db_concepts_path = gr.Textbox(label="Concepts List", placeholder="Path to JSON file with concepts to train.")

                    with gr.Accordion(open=False, label="Advanced"):
                        with gr.Row():
                            with gr.Column():
                                with gr.Column():
                                    gr.HTML(value="Tuning")
                                    db_use_cpu = gr.Checkbox(label="Use CPU Only (SLOW)", value=False)
                                    db_use_lora = gr.Checkbox(label="Use LORA", value=False)
                                    db_use_ema = gr.Checkbox(label="Use EMA", value=False)
                                    db_use_8bit_adam = gr.Checkbox(label="Use 8bit Adam", value=False)
                                    db_mixed_precision = gr.Dropdown(label="Mixed Precision", value="no", choices=list_floats())
                                    db_attention = gr.Dropdown(label="Memory Attention", value="default", choices=list_attention())

                                    db_not_cache_latents = gr.Checkbox(label="Don't Cache Latents", value=True)
                                    db_train_text_encoder = gr.Checkbox(label="Train Text Encoder", value=True)
                                    db_prior_loss_weight = gr.Number(label="Prior Loss Weight", value=1.0, precision=1)
                                    db_pad_tokens = gr.Checkbox(label="Pad Tokens", value=True)
                                    db_shuffle_tags = gr.Checkbox(label="Shuffle Tags", value=False)
                                    db_max_token_length = gr.Slider(label="Max Token Length", minimum=75, maximum=300, step=75)
                                    db_train_imagic_only = gr.Checkbox(label="Train Imagic Only", value=False)
                                with gr.Column():
                                    gr.HTML("Gradients")
                                    db_gradient_checkpointing = gr.Checkbox(label="Gradient Checkpointing", value=True)
                                    db_gradient_accumulation_steps = gr.Number(label="Gradient Accumulation Steps", precision=0, value=1)

                                with gr.Column():
                                    gr.HTML("Adam Advanced")
                                    db_adam_beta1 = gr.Number(label="Adam Beta 1", precision=1, value=0.9)
                                    db_adam_beta2 = gr.Number(label="Adam Beta 2", precision=3, value=0.999)
                                    db_adam_weight_decay = gr.Number(label="Adam Weight Decay", precision=3, value=0.01)
                                    db_adam_epsilon = gr.Number(label="Adam Epsilon", precision=8, value=0.00000001)

                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.HTML(value="")
                with gr.Tab("Concepts") as concept_tab:
                    with gr.Column(variant="panel"):
                        with gr.Tab("Concept 1"):
                            c1_max_steps, \
                            c1_instance_data_dir, c1_class_data_dir, c1_instance_prompt, \
                            c1_class_prompt, c1_num_class_images, c1_save_sample_prompt, c1_save_sample_template, c1_instance_token, \
                            c1_class_token, c1_num_class_images, c1_class_negative_prompt, c1_class_guidance_scale, \
                            c1_class_infer_steps, c1_save_sample_negative_prompt, c1_n_save_sample, c1_sample_seed, \
                            c1_save_guidance_scale, c1_save_infer_steps = build_concept_panel()

                        with gr.Tab("Concept 2"):
                            c2_max_steps, \
                            c2_instance_data_dir, c2_class_data_dir, c2_instance_prompt, \
                            c2_class_prompt, c2_num_class_images, c2_save_sample_prompt, c2_save_sample_template, c2_instance_token, \
                            c2_class_token, c2_num_class_images, c2_class_negative_prompt, c2_class_guidance_scale, \
                            c2_class_infer_steps, c2_save_sample_negative_prompt, c2_n_save_sample, c2_sample_seed, \
                            c2_save_guidance_scale, c2_save_infer_steps = build_concept_panel()

                        with gr.Tab("Concept 3"):
                            c3_max_steps, \
                            c3_instance_data_dir, c3_class_data_dir, c3_instance_prompt, \
                            c3_class_prompt, c3_num_class_images, c3_save_sample_prompt, c3_save_sample_template, c3_instance_token, \
                            c3_class_token, c3_num_class_images, c3_class_negative_prompt, c3_class_guidance_scale, \
                            c3_class_infer_steps, c3_save_sample_negative_prompt, c3_n_save_sample, c3_sample_seed, \
                            c3_save_guidance_scale, c3_save_infer_steps = build_concept_panel()

        with gr.Row(equal_height=True):
            db_interrupt_training = gr.Button(value="Cancel")
            db_train_model = gr.Button(value="Train", variant='primary')

        with gr.Row(equal_height=True):
            db_status = gr.Label(label='Output')

        db_create_from_hub.change(
            fn=lambda x: gr_show(x),
            inputs=[db_create_from_hub],
            outputs=[hub_row],
        )

        def disable_ema(x):
            db_use_ema.interactive = not x

        def disable_lora(x):
            db_use_lora.interactive = not x            

        db_use_lora.change(
            fn=disable_ema,
            inputs=[db_use_lora],
            outputs=[db_use_ema],
        )

        db_use_ema.change(
            fn=disable_lora,
            inputs=[db_use_ema],
            outputs=[db_use_lora],
        )

        db_create_from_hub.change(
            fn=lambda x: {
                hub_row: gr_show(x is True),
                local_row: gr_show(x is False)
            },
            inputs=[db_create_from_hub],
            outputs=[
                hub_row,
                local_row
            ]
        )

        db_model_name.change(
            fn=load_model_params,
            inputs=[db_model_name],
            outputs=[db_model_path, db_revision, db_v2, db_has_ema, db_src, db_scheduler, db_status]
        )

        db_use_concepts.change(
            fn=lambda x: {
                concept_tab: gr_show(x is True)
            },
            inputs=[db_use_concepts],
            outputs=[
                concept_tab
            ]
        )

        def sagemaker_train_dreambooth(
            db_create_new_db_model,
            db_new_model_name,
            db_new_model_src,
            db_new_model_scheduler,
            db_create_from_hub,
            db_new_model_url,
            db_new_model_token,
            db_new_model_extract_ema,
            db_model_name,
            db_lora_model_name,
            db_lora_weight,
            db_lora_txt_weight,
            db_train_imagic_only,
            db_use_subdir,
            db_custom_model_name,
            db_train_wizard_person,
            db_train_wizard_object,
            db_performance_wizard,
            db_training_instance_type,
            db_training_instance_count,
            db_concepts_s3uri,
            db_models_s3uri,
            db_adam_beta1,
            db_adam_beta2,
            db_adam_epsilon,
            db_adam_weight_decay,
            db_attention,
            db_center_crop,
            db_concepts_path,
            db_epoch_pause_frequency,
            db_epoch_pause_time,
            db_gradient_accumulation_steps,
            db_gradient_checkpointing,
            db_half_model,
            db_has_ema,
            db_hflip,
            db_learning_rate,
            db_lora_learning_rate,
            db_lora_txt_learning_rate,
            db_lr_scheduler,
            db_lr_warmup_steps,
            db_max_token_length,
            db_max_train_steps,
            db_mixed_precision,
            db_model_path,
            db_not_cache_latents,
            db_num_train_epochs,
            db_pad_tokens,
            db_pretrained_vae_name_or_path,
            db_prior_loss_weight,
            db_resolution,
            db_revision,
            db_sample_batch_size,
            db_save_class_txt,
            db_save_embedding_every,
            db_save_preview_every,
            db_save_use_global_counts,
            db_save_use_epochs,
            db_scale_lr,
            db_scheduler,
            db_src,
            db_shuffle_tags,
            db_train_batch_size,
            db_train_text_encoder,
            db_use_8bit_adam,
            db_use_concepts,
            db_use_cpu,
            db_use_ema,
            db_use_lora,
            db_v2,
            c1_class_data_dir,
            c1_class_guidance_scale,
            c1_class_infer_steps,
            c1_class_negative_prompt,
            c1_class_prompt,
            c1_class_token,
            c1_instance_data_dir,
            c1_instance_prompt,
            c1_instance_token,
            c1_max_steps,
            c1_n_save_sample,
            c1_num_class_images,
            c1_sample_seed,
            c1_save_guidance_scale,
            c1_save_infer_steps,
            c1_save_sample_negative_prompt,
            c1_save_sample_prompt,
            c1_save_sample_template,
            c2_class_data_dir,
            c2_class_guidance_scale,
            c2_class_infer_steps,
            c2_class_negative_prompt,
            c2_class_prompt,
            c2_class_token,
            c2_instance_data_dir,
            c2_instance_prompt,
            c2_instance_token,
            c2_max_steps,
            c2_n_save_sample,
            c2_num_class_images,
            c2_sample_seed,
            c2_save_guidance_scale,
            c2_save_infer_steps,
            c2_save_sample_negative_prompt,
            c2_save_sample_prompt,
            c2_save_sample_template,
            c3_class_data_dir,
            c3_class_guidance_scale,
            c3_class_infer_steps,
            c3_class_negative_prompt,
            c3_class_prompt,
            c3_class_token,
            c3_instance_data_dir,
            c3_instance_prompt,
            c3_instance_token,
            c3_max_steps,
            c3_n_save_sample,
            c3_num_class_images,
            c3_sample_seed,
            c3_save_guidance_scale,
            c3_save_infer_steps,
            c3_save_sample_negative_prompt,
            c3_save_sample_prompt,
            c3_save_sample_template
        ):

            db_config = [
                db_model_name,
                db_adam_beta1,
                db_adam_beta2,
                db_adam_epsilon,
                db_adam_weight_decay,
                db_attention,
                db_center_crop,
                db_concepts_path,
                db_custom_model_name,
                db_epoch_pause_frequency,
                db_epoch_pause_time,
                db_gradient_accumulation_steps,
                db_gradient_checkpointing,
                db_half_model,
                db_has_ema,
                db_hflip,
                db_learning_rate,
                db_lora_learning_rate,
                db_lora_txt_learning_rate,
                db_lr_scheduler,
                db_lr_warmup_steps,
                db_max_token_length,
                db_max_train_steps,
                db_mixed_precision,
                db_model_path,
                db_not_cache_latents,
                db_num_train_epochs,
                db_pad_tokens,
                db_pretrained_vae_name_or_path,
                db_prior_loss_weight,
                db_resolution,
                db_revision,
                db_sample_batch_size,
                db_save_class_txt,
                db_save_embedding_every,
                db_save_preview_every,
                db_save_use_global_counts,
                db_save_use_epochs,
                db_scale_lr,
                db_scheduler,
                db_src,
                db_shuffle_tags,
                db_train_batch_size,
                db_train_text_encoder,
                db_use_8bit_adam,
                db_use_concepts,
                db_use_cpu,
                db_use_ema,
                db_use_lora,
                db_v2,
                c1_class_data_dir,
                c1_class_guidance_scale,
                c1_class_infer_steps,
                c1_class_negative_prompt,
                c1_class_prompt,
                c1_class_token,
                c1_instance_data_dir,
                c1_instance_prompt,
                c1_instance_token,
                c1_max_steps,
                c1_n_save_sample,
                c1_num_class_images,
                c1_sample_seed,
                c1_save_guidance_scale,
                c1_save_infer_steps,
                c1_save_sample_negative_prompt,
                c1_save_sample_prompt,
                c1_save_sample_template,
                c2_class_data_dir,
                c2_class_guidance_scale,
                c2_class_infer_steps,
                c2_class_negative_prompt,
                c2_class_prompt,
                c2_class_token,
                c2_instance_data_dir,
                c2_instance_prompt,
                c2_instance_token,
                c2_max_steps,
                c2_n_save_sample,
                c2_num_class_images,
                c2_sample_seed,
                c2_save_guidance_scale,
                c2_save_infer_steps,
                c2_save_sample_negative_prompt,
                c2_save_sample_prompt,
                c2_save_sample_template,
                c3_class_data_dir,
                c3_class_guidance_scale,
                c3_class_infer_steps,
                c3_class_negative_prompt,
                c3_class_prompt,
                c3_class_token,
                c3_instance_data_dir,
                c3_instance_prompt,
                c3_instance_token,
                c3_max_steps,
                c3_n_save_sample,
                c3_num_class_images,
                c3_sample_seed,
                c3_save_guidance_scale,
                c3_save_infer_steps,
                c3_save_sample_negative_prompt,
                c3_save_sample_prompt,
                c3_save_sample_template
            ]

            dreambooth_config_id = str(uuid.uuid4())
            params = {'dreambooth_config_id': dreambooth_config_id}
            response = requests.post(url=f'{shared.api_endpoint}/sd/models', json=db_config, params=params)

            if response.status_code != 200:
                return {
                    db_status: gr.update(value=response.text)
                }

            train_args = {
                'train_dreambooth_settings': {
                    'db_create_new_db_model': db_create_new_db_model,
                    'db_new_model_name': db_new_model_name,
                    'db_new_model_src': db_new_model_src,
                    'db_new_model_scheduler': db_new_model_scheduler,
                    'db_create_from_hub': db_create_from_hub,
                    'db_new_model_url': db_new_model_url,
                    'db_new_model_token': db_new_model_token,
                    'db_new_model_extract_ema': db_new_model_extract_ema,
                    'db_model_name': db_model_name,
                    'db_lora_model_name': db_lora_model_name,
                    'db_lora_weight': db_lora_weight,
                    'db_lora_txt_weight': db_lora_txt_weight,
                    'db_train_imagic_only': db_train_imagic_only,
                    'db_use_subdir': db_use_subdir,
                    'db_custom_model_name': db_custom_model_name,
                    'db_train_wizard_person': db_train_wizard_person,
                    'db_train_wizard_object': db_train_wizard_object,
                    'db_performance_wizard': db_performance_wizard
                }
            }

            hyperparameters = {
                'train-args': json.dumps(json.dumps(train_args)),
                'train-task': 'dreambooth',
                'ckpt': '/opt/ml/input/data/models/{0}'.format(shared.sd_model.sd_model_name),
                'username': shared.username,
                'api-endpoint': shared.api_endpoint,
                'dreambooth-config-id': dreambooth_config_id
            }

            inputs = {
                'concepts': db_concepts_s3uri,
                'models': db_models_s3uri
            }

            data = {
                'training_job_name': '',
                'model_algorithm': 'stable-diffusion-webui',
                'model_hyperparameters': hyperparameters,
                'industrial_model': shared.industrial_model,
                'instance_type': db_training_instance_type,
                'instance_count': db_training_instance_count,
                'inputs': inputs
            }

            print(data)
            response = requests.post(url=f'{shared.api_endpoint}/train', json=data)
            if response.status_code == 200:
                return {
                    db_status: gr.update(value='Submit training job sucessful')
                }
            else:
                return {
                    db_status: gr.update(value=response.text)
                }


        db_train_model.click(
            fn=sagemaker_train_dreambooth,
            inputs=[
                db_create_new_db_model,
                db_new_model_name,
                db_new_model_src,
                db_new_model_scheduler,
                db_create_from_hub,
                db_new_model_url,
                db_new_model_token,
                db_new_model_extract_ema,
                db_model_name,
                db_lora_model_name,
                db_lora_weight,
                db_lora_txt_weight,
                db_train_imagic_only,
                db_use_subdir,
                db_custom_model_name,
                db_train_wizard_person,
                db_train_wizard_object,
                db_performance_wizard,
                db_training_instance_type,
                db_training_instance_count,
                db_concepts_s3uri,
                db_models_s3uri,
                db_adam_beta1,
                db_adam_beta2,
                db_adam_epsilon,
                db_adam_weight_decay,
                db_attention,
                db_center_crop,
                db_concepts_path,
                db_epoch_pause_frequency,
                db_epoch_pause_time,
                db_gradient_accumulation_steps,
                db_gradient_checkpointing,
                db_half_model,
                db_has_ema,
                db_hflip,
                db_learning_rate,
                db_lora_learning_rate,
                db_lora_txt_learning_rate,
                db_lr_scheduler,
                db_lr_warmup_steps,
                db_max_token_length,
                db_max_train_steps,
                db_mixed_precision,
                db_model_path,
                db_not_cache_latents,
                db_num_train_epochs,
                db_pad_tokens,
                db_pretrained_vae_name_or_path,
                db_prior_loss_weight,
                db_resolution,
                db_revision,
                db_sample_batch_size,
                db_save_class_txt,
                db_save_embedding_every,
                db_save_preview_every,
                db_save_use_global_counts,
                db_save_use_epochs,
                db_scale_lr,
                db_scheduler,
                db_src,
                db_shuffle_tags,
                db_train_batch_size,
                db_train_text_encoder,
                db_use_8bit_adam,
                db_use_concepts,
                db_use_cpu,
                db_use_ema,
                db_use_lora,
                db_v2,
		        c1_class_data_dir,
                c1_class_guidance_scale,
                c1_class_infer_steps,
                c1_class_negative_prompt,
                c1_class_prompt,
                c1_class_token,
                c1_instance_data_dir,
                c1_instance_prompt,
                c1_instance_token,
                c1_max_steps,
                c1_n_save_sample,
                c1_num_class_images,
                c1_sample_seed,
                c1_save_guidance_scale,
                c1_save_infer_steps,
                c1_save_sample_negative_prompt,
                c1_save_sample_prompt,
                c1_save_sample_template,
                c2_class_data_dir,
                c2_class_guidance_scale,
                c2_class_infer_steps,
                c2_class_negative_prompt,
                c2_class_prompt,
                c2_class_token,
                c2_instance_data_dir,
                c2_instance_prompt,
                c2_instance_token,
                c2_max_steps,
                c2_n_save_sample,
                c2_num_class_images,
                c2_sample_seed,
                c2_save_guidance_scale,
                c2_save_infer_steps,
                c2_save_sample_negative_prompt,
                c2_save_sample_prompt,
                c2_save_sample_template,
                c3_class_data_dir,
                c3_class_guidance_scale,
                c3_class_infer_steps,
                c3_class_negative_prompt,
                c3_class_prompt,
                c3_class_token,
                c3_instance_data_dir,
                c3_instance_prompt,
                c3_instance_token,
                c3_max_steps,
                c3_n_save_sample,
                c3_num_class_images,
                c3_sample_seed,
                c3_save_guidance_scale,
                c3_save_infer_steps,
                c3_save_sample_negative_prompt,
                c3_save_sample_prompt,
                c3_save_sample_template                
            ],
            outputs=[
                db_status
            ]
        )

        db_interrupt_training.click(
            fn=lambda: shared.state.interrupt(),
            inputs=[],
            outputs=[],
        )

    return (dreambooth_interface, "Dreambooth", "dreambooth_interface"),


def build_concept_panel():
    with gr.Column():
        max_steps = gr.Number(label="Maximum Training Steps", value=-1, precision=0)
        gr.HTML(value="Directories")
        instance_data_dir = gr.Textbox(label='Dataset Directory',
                                       placeholder="Path to directory with input images")
        class_data_dir = gr.Textbox(label='Classification Dataset Directory',
                                    placeholder="(Optional) Path to directory with "
                                                "classification/regularization images")
    with gr.Column():
        gr.HTML(value="Filewords")
        instance_token = gr.Textbox(label='Instance Token',
                                    placeholder="When using [filewords], this is the subject to use when building prompts.")
        class_token = gr.Textbox(label='Class Token',
                                 placeholder="When using [filewords], this is the class to use when building prompts.")

    with gr.Column():
        gr.HTML(value="Prompts")
        instance_prompt = gr.Textbox(label="Instance Prompt",
                                     placeholder="Optionally use [filewords] to read image "
                                                 "captions from files.")
        class_prompt = gr.Textbox(label="Class Prompt",
                                  placeholder="Optionally use [filewords] to read image "
                                              "captions from files.")
        class_negative_prompt = gr.Textbox(label="Classification Image Negative Prompt")
        save_sample_prompt = gr.Textbox(label="Sample Image Prompt",
                                        placeholder="Leave blank to use instance prompt. "
                                                    "Optionally use [filewords] to base "
                                                    "sample captions on instance images.")
        sample_template = gr.Textbox(label="Sample Prompt Template File",
                                     placeholder="Enter the path to a txt file containing sample prompts.")
        save_sample_negative_prompt = gr.Textbox(label="Sample Image Negative Prompt")

    with gr.Column():
        gr.HTML("Image Generation")
        num_class_images = gr.Number(label='Total Number of Class/Reg Images', value=0, precision=0)
        class_guidance_scale = gr.Number(label="Classification CFG Scale", value=7.5, max=12, min=1, precision=2)
        class_infer_steps = gr.Number(label="Classification Steps", value=40, min=10, max=200, precision=0)
        n_save_sample = gr.Number(label="Number of Samples to Generate", value=1, precision=0)
        sample_seed = gr.Number(label="Sample Seed", value=-1, precision=0)
        save_guidance_scale = gr.Number(label="Sample CFG Scale", value=7.5, max=12, min=1, precision=2)
        save_infer_steps = gr.Number(label="Sample Steps", value=40, min=10, max=200, precision=0)
    return [max_steps, instance_data_dir, class_data_dir, instance_prompt, class_prompt,
            num_class_images,
            save_sample_prompt, sample_template, instance_token, class_token, num_class_images, class_negative_prompt,
            class_guidance_scale, class_infer_steps, save_sample_negative_prompt, n_save_sample, sample_seed,
            save_guidance_scale, save_infer_steps]

def get_sd_models():
    api_endpoint = os.environ['api_endpoint']
    names = set()
    if api_endpoint != '':
        response = requests.get(url=f'{api_endpoint}/sd/models')
        if response.status_code == 200:
            model_list = json.loads(response.text)
            for model in model_list:
                names.add(model['title'])
    return list(names)

script_callbacks.on_ui_tabs(on_ui_tabs)
